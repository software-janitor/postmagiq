"""Service for analytics import and processing."""

import csv
import io
import logging
from datetime import date, datetime
from typing import Optional, Union
from uuid import UUID

import pandas as pd
from sqlalchemy import desc, func
from sqlmodel import select

from runner.content.ids import coerce_uuid, normalize_user_id
from runner.content.models import (
    AnalyticsImportResponse,
    PostMetricResponse,
    AnalyticsSummary,
    DailyMetricResponse,
    FollowerMetricResponse,
    AudienceDemographicResponse,
    PostDemographicResponse,
)
from runner.db.engine import get_session
from runner.db.models import (
    AnalyticsImport,
    PostMetric,
    DailyMetric,
    FollowerMetric,
    AudienceDemographic,
    PostDemographic,
)

logger = logging.getLogger(__name__)


class AnalyticsService:
    """Service for importing and querying analytics data."""

    def __init__(self):
        pass

    def _resolve_user_id(self, user_id: Union[str, UUID]) -> UUID:
        """Normalize user IDs for storage."""
        uid = normalize_user_id(user_id)
        if not uid:
            raise ValueError("Invalid user_id")
        return uid

    def _resolve_import_id(self, import_id: Union[str, UUID]) -> UUID:
        """Normalize import IDs for storage."""
        iid = coerce_uuid(import_id)
        if not iid:
            raise ValueError("Invalid import_id")
        return iid

    def _to_date(self, value: Optional[Union[str, date, datetime]]) -> Optional[date]:
        """Normalize date inputs for SQLModel."""
        if value is None:
            return None
        if isinstance(value, date) and not isinstance(value, datetime):
            return value
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, str):
            try:
                return date.fromisoformat(value[:10])
            except ValueError:
                return None
        return None

    def _update_import(self, import_id: Union[str, UUID], **kwargs) -> None:
        """Update analytics import fields."""
        iid = self._resolve_import_id(import_id)
        with get_session() as session:
            record = session.get(AnalyticsImport, iid)
            if not record:
                return
            for key, value in kwargs.items():
                if hasattr(record, key):
                    setattr(record, key, value)
            session.add(record)
            session.commit()
            session.refresh(record)

    # =========================================================================
    # Import Operations
    # =========================================================================

    def create_import(
        self,
        user_id: Union[str, UUID],
        platform_name: str,
        filename: str,
    ) -> str:
        """Create an analytics import record."""
        uid = self._resolve_user_id(user_id)
        record = AnalyticsImport(
            user_id=uid,
            platform_name=platform_name,
            filename=filename,
            status="pending",
            import_date=datetime.utcnow(),
        )
        with get_session() as session:
            session.add(record)
            session.commit()
            session.refresh(record)
            return str(record.id)

    def process_file(
        self,
        user_id: Union[str, UUID],
        import_id: Union[str, UUID],
        platform_name: str,
        file_content: bytes,
        filename: str,
    ) -> dict:
        """Process a file (CSV or XLS/XLSX) and insert metrics."""
        try:
            # Detect file type by content magic bytes (more reliable than extension)
            is_excel = False

            # Check for Excel file signatures
            # XLSX/XLSM/etc (ZIP-based): starts with PK (0x504B)
            # XLS (older): starts with 0xD0CF11E0
            if len(file_content) >= 4:
                if file_content[:2] == b'PK':  # ZIP-based (xlsx, xlsm)
                    is_excel = True
                elif file_content[:4] == b'\xd0\xcf\x11\xe0':  # OLE (xls)
                    is_excel = True
                elif file_content[:8] == b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1':  # Full OLE signature
                    is_excel = True

            # Fallback to extension if content check didn't detect Excel
            if not is_excel:
                file_ext = filename.lower().split(".")[-1] if "." in filename else "csv"
                if file_ext in ("xls", "xlsx", "xlsm"):
                    is_excel = True

            if is_excel:
                # Handle Excel files with platform-specific parsers
                excel_file = pd.ExcelFile(io.BytesIO(file_content))

                if platform_name == "linkedin":
                    # Use dedicated LinkedIn Excel parser
                    return self._parse_linkedin_excel(
                        user_id, import_id, excel_file, filename
                    )
                else:
                    # Generic: combine all sheets into CSV
                    all_dfs = []
                    for sheet_name in excel_file.sheet_names:
                        df = pd.read_excel(excel_file, sheet_name=sheet_name)
                        if not df.empty:
                            all_dfs.append(df)

                    if not all_dfs:
                        return {
                            "success": False,
                            "error": "No data found in Excel file."
                        }

                    combined_df = pd.concat(all_dfs, ignore_index=True)
                    csv_content = combined_df.to_csv(index=False)
            else:
                # Try different encodings for CSV
                csv_content = None
                for encoding in ["utf-8", "utf-8-sig", "latin-1", "cp1252"]:
                    try:
                        csv_content = file_content.decode(encoding)
                        break
                    except UnicodeDecodeError:
                        continue

                if csv_content is None:
                    return {
                        "success": False,
                        "error": "Could not decode file. Please upload a CSV or Excel file."
                    }

            return self.process_csv(user_id, import_id, platform_name, csv_content)

        except Exception as e:
            # Update import with error
            self._update_import(
                import_id,
                status="error",
                error_message=str(e),
            )
            return {"success": False, "error": str(e)}

    def process_csv(
        self,
        user_id: Union[str, UUID],
        import_id: Union[str, UUID],
        platform_name: str,
        csv_content: str,
    ) -> dict:
        """Process a CSV file and insert metrics."""
        try:
            uid = self._resolve_user_id(user_id)
            iid = self._resolve_import_id(import_id)

            # Parse CSV based on platform
            if platform_name == "linkedin":
                metrics = self._parse_linkedin_csv(csv_content)
            elif platform_name == "threads":
                metrics = self._parse_threads_csv(csv_content)
            elif platform_name in ("x", "twitter"):
                metrics = self._parse_twitter_csv(csv_content)
            else:
                raise ValueError(f"Unknown platform: {platform_name}")

            # Create metric records
            records = []
            for m in metrics:
                metric_date = self._to_date(m.get("metric_date")) or date.today()
                records.append(
                    PostMetric(
                        user_id=uid,
                        platform_name=platform_name,
                        import_id=iid,
                        external_url=m.get("url"),
                        post_date=self._to_date(m.get("post_date")),
                        impressions=m.get("impressions"),
                        engagement_count=m.get("engagement_count"),
                        engagement_rate=m.get("engagement_rate"),
                        likes=m.get("likes"),
                        comments=m.get("comments"),
                        shares=m.get("shares"),
                        clicks=m.get("clicks"),
                        metric_date=metric_date,
                    )
                )

            # Batch insert
            with get_session() as session:
                session.add_all(records)
                session.commit()
            count = len(records)

            # Update import status
            self._update_import(
                import_id,
                status="processed",
                row_count=count,
            )

            return {"success": True, "rows_imported": count}

        except Exception as e:
            # Update import with error
            self._update_import(
                import_id,
                status="error",
                error_message=str(e),
            )
            return {"success": False, "error": str(e)}

    def _parse_linkedin_excel(
        self,
        user_id: Union[str, UUID],
        import_id: Union[str, UUID],
        excel_file: pd.ExcelFile,
        filename: str,
    ) -> dict:
        """Parse LinkedIn Excel export with multiple sheets.

        Content export has: DISCOVERY, ENGAGEMENT, TOP POSTS, FOLLOWERS, DEMOGRAPHICS
        Post analytics has: PERFORMANCE, TOP DEMOGRAPHICS

        Uses upsert for deduplication - re-uploading same data updates existing records.
        """
        sheet_names_upper = [s.upper() for s in excel_file.sheet_names]
        logger.info(f"LinkedIn Excel sheets found: {excel_file.sheet_names}")
        stats = {
            "daily_metrics": 0,
            "follower_metrics": 0,
            "post_metrics": 0,
            "audience_demographics": 0,
            "post_demographics": 0,
        }

        try:
            uid = self._resolve_user_id(user_id)
            iid = self._resolve_import_id(import_id)
            # Detect file type by sheets
            is_post_analytics = "PERFORMANCE" in sheet_names_upper
            is_content_export = "ENGAGEMENT" in sheet_names_upper or "TOP POSTS" in sheet_names_upper

            # Determine import type
            import_type = "post_analytics" if is_post_analytics else "content_export"

            if is_content_export:
                # ENGAGEMENT sheet → daily_metrics (aggregate daily stats)
                if "ENGAGEMENT" in sheet_names_upper:
                    daily_records = self._parse_linkedin_engagement_to_daily(
                        uid, iid, excel_file
                    )
                    if daily_records:
                        stats["daily_metrics"] = self._upsert_daily_metrics_batch(daily_records)

                # TOP POSTS sheet → post_metrics (impressions by URL)
                if "TOP POSTS" in sheet_names_upper:
                    post_metrics = self._parse_linkedin_top_posts_sheet(excel_file)
                    for m in post_metrics:
                        if m.get("url"):
                            record = {
                                "user_id": uid,
                                "platform_name": "linkedin",
                                "import_id": iid,
                                "external_url": m.get("url"),
                                "post_date": m.get("post_date"),
                                "impressions": m.get("impressions"),
                                "engagement_count": m.get("engagement_count"),
                                "metric_date": m.get("metric_date", datetime.now().strftime("%Y-%m-%d")),
                            }
                            self._upsert_post_metric(record)
                            stats["post_metrics"] += 1

                # FOLLOWERS sheet → follower_metrics
                if "FOLLOWERS" in sheet_names_upper:
                    follower_records = self._parse_linkedin_followers_sheet(
                        uid, iid, excel_file
                    )
                    if follower_records:
                        stats["follower_metrics"] = self._upsert_follower_metrics_batch(follower_records)

                # DEMOGRAPHICS sheet → audience_demographics
                if "DEMOGRAPHICS" in sheet_names_upper:
                    demo_records = self._parse_linkedin_demographics_sheet(
                        uid, iid, excel_file
                    )
                    if demo_records:
                        stats["audience_demographics"] = self._upsert_audience_demographics_batch(demo_records)

            if is_post_analytics:
                # PERFORMANCE sheet → post_metrics with delta calculation
                performance_data = self._parse_linkedin_post_performance(excel_file)
                for m in performance_data:
                    if m.get("url"):
                        record = {
                            "user_id": uid,
                            "platform_name": "linkedin",
                            "import_id": iid,
                            "external_url": m.get("url"),
                            "post_date": m.get("post_date"),
                            "impressions": m.get("impressions"),
                            "engagement_count": m.get("engagement_count"),
                            "engagement_rate": m.get("engagement_rate"),
                            "likes": m.get("likes"),
                            "comments": m.get("comments"),
                            "shares": m.get("shares"),
                            "clicks": m.get("clicks"),
                            "metric_date": m.get("metric_date", datetime.now().strftime("%Y-%m-%d")),
                        }
                        self._upsert_post_metric(record)
                        stats["post_metrics"] += 1

                # TOP DEMOGRAPHICS sheet → post_demographics
                if "TOP DEMOGRAPHICS" in sheet_names_upper:
                    post_demo_records = self._parse_linkedin_post_demographics(
                        uid, iid, excel_file, performance_data
                    )
                    if post_demo_records:
                        stats["post_demographics"] = self._upsert_post_demographics_batch(post_demo_records)

            total_rows = sum(stats.values())
            logger.info(f"LinkedIn import stats: {stats}")
            if total_rows == 0:
                return {
                    "success": False,
                    "error": f"Could not find recognizable data in LinkedIn export. Sheets: {excel_file.sheet_names}"
                }

            # Update import status with import_type
            self._update_import(
                import_id,
                status="processed",
                row_count=total_rows,
                import_type=import_type,
            )

            return {
                "success": True,
                "rows_imported": total_rows,
                "import_type": import_type,
                "stats": stats,
            }

        except Exception as e:
            self._update_import(
                import_id,
                status="error",
                error_message=str(e),
            )
            return {"success": False, "error": str(e)}

    def _parse_linkedin_post_performance(self, excel_file: pd.ExcelFile) -> list[dict]:
        """Parse PERFORMANCE sheet from LinkedIn post analytics."""
        metrics = []

        # Find the PERFORMANCE sheet (case-insensitive)
        sheet_name = None
        for s in excel_file.sheet_names:
            if s.upper() == "PERFORMANCE":
                sheet_name = s
                break

        if not sheet_name:
            return metrics

        df = pd.read_excel(excel_file, sheet_name=sheet_name, header=None)

        # This sheet has key-value pairs in columns 0 and 1
        data = {}
        for _, row in df.iterrows():
            key = str(row[0]).strip() if pd.notna(row[0]) else ""
            val = row[1] if len(row) > 1 and pd.notna(row[1]) else None

            if key == "Post URL" and val:
                data["url"] = str(val)
            elif key == "Post Date" and val:
                data["post_date"] = self._parse_date(str(val))
                data["metric_date"] = data["post_date"]
            elif key == "Impressions" and val:
                data["impressions"] = self._safe_int(val)
            elif key == "Reactions" and val:
                data["likes"] = self._safe_int(val)
            elif key == "Comments" and val:
                data["comments"] = self._safe_int(val)
            elif key == "Reposts" and val:
                data["shares"] = self._safe_int(val)
            elif key == "Visits to links in this post" and val:
                data["clicks"] = self._safe_int(val)

        if data.get("url") or data.get("impressions"):
            # Calculate engagement
            likes = data.get("likes") or 0
            comments = data.get("comments") or 0
            shares = data.get("shares") or 0
            data["engagement_count"] = likes + comments + shares

            if data.get("impressions") and data["impressions"] > 0:
                data["engagement_rate"] = round(
                    data["engagement_count"] / data["impressions"] * 100, 2
                )

            if not data.get("metric_date"):
                data["metric_date"] = datetime.now().strftime("%Y-%m-%d")

            metrics.append(data)

        return metrics

    def _parse_linkedin_top_posts_sheet(self, excel_file: pd.ExcelFile) -> list[dict]:
        """Parse TOP POSTS sheet from LinkedIn content export."""
        metrics = []

        sheet_name = None
        for s in excel_file.sheet_names:
            if s.upper() == "TOP POSTS":
                sheet_name = s
                break

        if not sheet_name:
            return metrics

        df = pd.read_excel(excel_file, sheet_name=sheet_name, header=None)

        # Find the header row (contains "Post URL")
        header_row = None
        for i, row in df.iterrows():
            row_values = [str(v).strip() if pd.notna(v) else "" for v in row]
            if "Post URL" in row_values:
                header_row = i
                break

        if header_row is None:
            return metrics

        # Parse data rows after header
        for i in range(header_row + 1, len(df)):
            row = df.iloc[i]

            # LinkedIn TOP POSTS has two tables side by side
            # Left table (columns 0-2): by Engagements
            # Right table (columns 4-6): by Impressions

            # Try left table first (by engagements)
            url_left = row[0] if pd.notna(row[0]) and str(row[0]).startswith("http") else None
            if url_left:
                metric = {
                    "url": str(url_left),
                    "post_date": self._parse_date(str(row[1])) if pd.notna(row[1]) else None,
                    "engagement_count": self._safe_int(row[2]) if len(row) > 2 else None,
                }
                if metric.get("post_date"):
                    metric["metric_date"] = metric["post_date"]
                else:
                    metric["metric_date"] = datetime.now().strftime("%Y-%m-%d")
                metrics.append(metric)

            # Try right table (by impressions) - usually columns 4-6
            if len(row) > 4:
                url_right = row[4] if pd.notna(row[4]) and str(row[4]).startswith("http") else None
                if url_right and str(url_right) != str(url_left):  # Avoid duplicates
                    metric = {
                        "url": str(url_right),
                        "post_date": self._parse_date(str(row[5])) if len(row) > 5 and pd.notna(row[5]) else None,
                        "impressions": self._safe_int(row[6]) if len(row) > 6 else None,
                    }
                    if metric.get("post_date"):
                        metric["metric_date"] = metric["post_date"]
                    else:
                        metric["metric_date"] = datetime.now().strftime("%Y-%m-%d")
                    metrics.append(metric)

        return metrics

    def _parse_linkedin_engagement_to_daily(
        self,
        user_id: UUID,
        import_id: UUID,
        excel_file: pd.ExcelFile,
    ) -> list[dict]:
        """Parse ENGAGEMENT sheet into daily_metrics records."""
        records = []

        sheet_name = None
        for s in excel_file.sheet_names:
            if s.upper() == "ENGAGEMENT":
                sheet_name = s
                break

        if not sheet_name:
            return records

        df = pd.read_excel(excel_file, sheet_name=sheet_name)

        # Expected columns: Date, Impressions, Engagements
        for _, row in df.iterrows():
            date_val = row.get("Date")
            if pd.isna(date_val):
                continue

            metric_date = self._parse_date(str(date_val))
            records.append(
                {
                    "user_id": user_id,
                    "platform_name": "linkedin",
                    "metric_date": metric_date,
                    "impressions": self._safe_int(row.get("Impressions")),
                    "engagements": self._safe_int(row.get("Engagements")),
                    "import_id": import_id,
                }
            )

        return records

    def _parse_linkedin_followers_sheet(
        self,
        user_id: UUID,
        import_id: UUID,
        excel_file: pd.ExcelFile,
    ) -> list[dict]:
        """Parse FOLLOWERS sheet from LinkedIn content export.

        Format:
        Row 0: "Total followers on DATE:" | total_count
        Row 1: empty
        Row 2: "Date" | "New followers"
        Row 3+: date | new_followers_count
        """
        records = []

        sheet_name = None
        for s in excel_file.sheet_names:
            if s.upper() == "FOLLOWERS":
                sheet_name = s
                break

        if not sheet_name:
            logger.info("FOLLOWERS sheet not found")
            return records

        df = pd.read_excel(excel_file, sheet_name=sheet_name, header=None)
        logger.info(f"FOLLOWERS sheet has {len(df)} rows")

        # Extract total followers from row 0 (e.g., "Total followers on 1/12/2026: | 791")
        total_followers = None
        if len(df) > 0:
            row0_col0 = str(df.iloc[0, 0]) if pd.notna(df.iloc[0, 0]) else ""
            if "total followers" in row0_col0.lower():
                total_followers = self._safe_int(df.iloc[0, 1])
                logger.info(f"FOLLOWERS total from header: {total_followers}")

        # Find header row (contains "Date")
        header_row = None
        for i, row in df.iterrows():
            col0 = str(row[0]).strip().lower() if pd.notna(row[0]) else ""
            if col0 == "date":
                header_row = i
                break

        if header_row is None:
            logger.warning("FOLLOWERS sheet: no header row found")
            return records

        # Parse data rows after header
        for i in range(header_row + 1, len(df)):
            row = df.iloc[i]
            date_val = row[0] if pd.notna(row[0]) else None
            new_followers_val = row[1] if len(row) > 1 and pd.notna(row[1]) else None

            if date_val is None:
                continue

            metric_date = self._parse_date(str(date_val))
            new_followers = self._safe_int(new_followers_val)

            if new_followers is not None:
                records.append(
                    {
                        "user_id": user_id,
                        "platform_name": "linkedin",
                        "metric_date": metric_date,
                        "new_followers": new_followers,
                        "total_followers": total_followers,
                        "import_id": import_id,
                    }
                )

        logger.info(f"Parsed {len(records)} follower records")
        return records

    def _parse_linkedin_demographics_sheet(
        self,
        user_id: UUID,
        import_id: UUID,
        excel_file: pd.ExcelFile,
    ) -> list[dict]:
        """Parse DEMOGRAPHICS sheet from LinkedIn content export.

        Format: Category (Job titles, Locations, etc.) | Value | Percentage
        Each row has: Category | Value | Percentage
        """
        records = []

        sheet_name = None
        for s in excel_file.sheet_names:
            if s.upper() == "DEMOGRAPHICS":
                sheet_name = s
                break

        if not sheet_name:
            logger.info("DEMOGRAPHICS sheet not found")
            return records

        df = pd.read_excel(excel_file, sheet_name=sheet_name, header=None)
        logger.info(f"DEMOGRAPHICS sheet has {len(df)} rows")

        # Category mapping (normalize category names from LinkedIn format)
        category_mapping = {
            "job titles": "job_title",
            "job title": "job_title",
            "job functions": "job_function",
            "job function": "job_function",
            "locations": "location",
            "location": "location",
            "industries": "industry",
            "industry": "industry",
            "seniority": "seniority",
            "company size": "company_size",
            "company sizes": "company_size",
        }

        metric_date = datetime.now().strftime("%Y-%m-%d")

        for i, row in df.iterrows():
            # Each row has: Category | Value | Percentage
            col0 = str(row[0]).strip() if pd.notna(row[0]) else ""
            col1 = str(row[1]).strip() if len(row) > 1 and pd.notna(row[1]) else ""
            col2 = row[2] if len(row) > 2 and pd.notna(row[2]) else None

            # Skip header row
            if col0.lower() in ("top demographics", "category"):
                continue

            # Map category name
            col0_lower = col0.lower()
            category = category_mapping.get(col0_lower)
            if not category:
                continue

            # Parse percentage from column 2
            percentage = None
            if col2 is not None:
                if isinstance(col2, (int, float)):
                    percentage = float(col2)
                    # Convert decimal to percentage (0.052963 -> 5.30)
                    if 0 < percentage < 1:
                        percentage = percentage * 100
                elif isinstance(col2, str):
                    try:
                        percentage = float(col2.replace("%", "").strip())
                    except ValueError:
                        continue

            if col1 and percentage is not None:
                records.append(
                    {
                        "user_id": user_id,
                        "platform_name": "linkedin",
                        "category": category,
                        "value": col1,
                        "percentage": round(percentage, 2),
                        "import_id": import_id,
                        "metric_date": metric_date,
                    }
                )

        logger.info(f"Parsed {len(records)} audience demographics records")
        return records

    def _parse_linkedin_post_demographics(
        self,
        user_id: UUID,
        import_id: UUID,
        excel_file: pd.ExcelFile,
        performance_data: list[dict],
    ) -> list[dict]:
        """Parse TOP DEMOGRAPHICS sheet from LinkedIn post analytics.

        This sheet shows who engaged with a specific post.
        Format: Category | Value | % (all in each row)
        We need the external_url from performance_data to link demographics to the post.
        """
        records = []

        sheet_name = None
        for s in excel_file.sheet_names:
            if s.upper() == "TOP DEMOGRAPHICS":
                sheet_name = s
                break

        if not sheet_name:
            logger.info("TOP DEMOGRAPHICS sheet not found")
            return records

        # Get the post URL from performance data
        external_url = None
        for p in performance_data:
            if p.get("url"):
                external_url = p["url"]
                break

        logger.info(f"TOP DEMOGRAPHICS: external_url={external_url}, performance_data_count={len(performance_data)}")
        if not external_url:
            logger.warning("TOP DEMOGRAPHICS: no URL found in performance data")
            return records

        df = pd.read_excel(excel_file, sheet_name=sheet_name, header=None)
        logger.info(f"TOP DEMOGRAPHICS sheet has {len(df)} rows")

        # Category mapping (normalize category names)
        category_mapping = {
            "company size": "company_size",
            "job title": "job_title",
            "job function": "job_function",
            "location": "location",
            "industry": "industry",
            "seniority": "seniority",
            "company": "company",
        }

        for i, row in df.iterrows():
            # Each row has: Category | Value | Percentage
            col0 = str(row[0]).strip() if pd.notna(row[0]) else ""
            col1 = str(row[1]).strip() if len(row) > 1 and pd.notna(row[1]) else ""
            col2 = row[2] if len(row) > 2 and pd.notna(row[2]) else None

            # Skip header row
            if col0.lower() == "category":
                continue

            # Map category name
            col0_lower = col0.lower()
            category = category_mapping.get(col0_lower)
            if not category:
                continue

            # Parse percentage from column 2
            percentage = None
            if col2 is not None:
                if isinstance(col2, (int, float)):
                    percentage = float(col2)
                    # Convert decimal to percentage (0.299 -> 29.9)
                    if 0 < percentage < 1:
                        percentage = percentage * 100
                elif isinstance(col2, str):
                    try:
                        percentage = float(col2.replace("%", "").strip())
                    except ValueError:
                        continue

            if col1 and percentage is not None:
                records.append(
                    {
                        "user_id": user_id,
                        "platform_name": "linkedin",
                        "external_url": external_url,
                        "category": category,
                        "value": col1,
                        "percentage": round(percentage, 2),
                        "import_id": import_id,
                    }
                )

        logger.info(f"Parsed {len(records)} post demographics records")
        return records

    def _parse_linkedin_csv(self, csv_content: str) -> list[dict]:
        """Parse LinkedIn analytics CSV export (fallback for CSV files).

        LinkedIn CSV format typically has columns:
        Date, Impressions, Unique impressions, Clicks, Reactions, Comments, Shares, Engagement rate
        """
        metrics = []
        reader = csv.DictReader(io.StringIO(csv_content))

        for row in reader:
            # Handle various LinkedIn CSV column names
            metric = {
                "metric_date": row.get("Date", ""),
                "impressions": self._safe_int(row.get("Impressions", row.get("Views", ""))),
                "clicks": self._safe_int(row.get("Clicks", "")),
                "likes": self._safe_int(row.get("Reactions", row.get("Likes", ""))),
                "comments": self._safe_int(row.get("Comments", "")),
                "shares": self._safe_int(row.get("Shares", row.get("Reposts", ""))),
                "url": row.get("Post URL", row.get("URL", "")),
            }

            # Calculate engagement
            engagement = (metric["likes"] or 0) + (metric["comments"] or 0) + (metric["shares"] or 0)
            metric["engagement_count"] = engagement

            # Calculate engagement rate
            if metric["impressions"] and metric["impressions"] > 0:
                metric["engagement_rate"] = round(engagement / metric["impressions"] * 100, 2)

            # Parse date if present
            if metric["metric_date"]:
                metric["metric_date"] = self._parse_date(metric["metric_date"])
            else:
                metric["metric_date"] = datetime.now().strftime("%Y-%m-%d")

            metrics.append(metric)

        return metrics

    def _parse_threads_csv(self, csv_content: str) -> list[dict]:
        """Parse Threads analytics export.

        Threads format may vary, common columns:
        post_id, views, likes, replies, reposts, quotes
        """
        metrics = []
        reader = csv.DictReader(io.StringIO(csv_content))

        for row in reader:
            metric = {
                "metric_date": row.get("date", row.get("Date", datetime.now().strftime("%Y-%m-%d"))),
                "impressions": self._safe_int(row.get("views", row.get("Views", ""))),
                "likes": self._safe_int(row.get("likes", row.get("Likes", ""))),
                "comments": self._safe_int(row.get("replies", row.get("Replies", row.get("comments", "")))),
                "shares": self._safe_int(row.get("reposts", row.get("Reposts", ""))) +
                         self._safe_int(row.get("quotes", row.get("Quotes", ""))),
                "url": row.get("url", row.get("URL", row.get("post_url", ""))),
            }

            # Calculate engagement
            engagement = (metric["likes"] or 0) + (metric["comments"] or 0) + (metric["shares"] or 0)
            metric["engagement_count"] = engagement

            # Calculate engagement rate
            if metric["impressions"] and metric["impressions"] > 0:
                metric["engagement_rate"] = round(engagement / metric["impressions"] * 100, 2)

            # Parse date
            if metric["metric_date"]:
                metric["metric_date"] = self._parse_date(metric["metric_date"])

            metrics.append(metric)

        return metrics

    def _parse_twitter_csv(self, csv_content: str) -> list[dict]:
        """Parse Twitter/X analytics CSV export.

        Twitter CSV format typically has columns:
        Tweet id, Tweet permalink, Tweet text, time, impressions, engagements,
        engagement rate, retweets, replies, likes, user profile clicks, url clicks
        """
        metrics = []
        reader = csv.DictReader(io.StringIO(csv_content))

        for row in reader:
            metric = {
                "metric_date": row.get("time", row.get("Date", "")),
                "impressions": self._safe_int(row.get("impressions", row.get("Impressions", ""))),
                "engagement_count": self._safe_int(row.get("engagements", row.get("Engagements", ""))),
                "likes": self._safe_int(row.get("likes", row.get("Likes", ""))),
                "comments": self._safe_int(row.get("replies", row.get("Replies", ""))),
                "shares": self._safe_int(row.get("retweets", row.get("Retweets", ""))),
                "clicks": self._safe_int(row.get("url clicks", row.get("URL clicks", ""))) +
                         self._safe_int(row.get("user profile clicks", "")),
                "url": row.get("Tweet permalink", row.get("URL", "")),
            }

            # Parse engagement rate if provided
            rate_str = row.get("engagement rate", row.get("Engagement rate", ""))
            if rate_str:
                metric["engagement_rate"] = self._safe_float(rate_str.replace("%", ""))
            elif metric["impressions"] and metric["impressions"] > 0 and metric["engagement_count"]:
                metric["engagement_rate"] = round(metric["engagement_count"] / metric["impressions"] * 100, 2)

            # Parse date
            if metric["metric_date"]:
                metric["metric_date"] = self._parse_date(metric["metric_date"])
            else:
                metric["metric_date"] = datetime.now().strftime("%Y-%m-%d")

            metrics.append(metric)

        return metrics

    def _safe_int(self, value) -> Optional[int]:
        """Safely convert value to int."""
        if value is None or (isinstance(value, str) and value.strip() == ""):
            return None
        try:
            # Handle comma-formatted numbers
            return int(str(value).replace(",", "").strip())
        except (ValueError, TypeError):
            return None

    def _safe_float(self, value) -> Optional[float]:
        """Safely convert value to float."""
        if value is None or (isinstance(value, str) and value.strip() == ""):
            return None
        try:
            return float(str(value).replace(",", "").strip())
        except (ValueError, TypeError):
            return None

    def _parse_date(self, date_str: str) -> str:
        """Parse various date formats to YYYY-MM-DD."""
        date_str = str(date_str).strip()

        # Try common formats
        formats = [
            "%Y-%m-%d",
            "%m/%d/%Y",
            "%d/%m/%Y",
            "%Y/%m/%d",
            "%B %d, %Y",
            "%b %d, %Y",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d %H:%M:%S",
        ]

        for fmt in formats:
            try:
                dt = datetime.strptime(date_str, fmt)
                return dt.strftime("%Y-%m-%d")
            except ValueError:
                continue

        # If no format matches, return as-is or today
        return date_str if len(date_str) == 10 else datetime.now().strftime("%Y-%m-%d")

    def _upsert_post_metric(self, record: dict) -> None:
        """Upsert a post metric with delta calculation."""
        uid = record["user_id"]
        platform = record.get("platform_name")
        url = record.get("external_url")
        if not platform or not url:
            return

        metric_date = self._to_date(record.get("metric_date")) or date.today()
        post_date = self._to_date(record.get("post_date"))

        with get_session() as session:
            existing = session.exec(
                select(PostMetric).where(
                    PostMetric.user_id == uid,
                    PostMetric.platform_name == platform,
                    PostMetric.external_url == url,
                )
            ).first()

            if existing:
                if record.get("impressions") is not None:
                    existing.impressions_delta = (record.get("impressions") or 0) - (existing.impressions or 0)
                    existing.impressions = record.get("impressions")
                if record.get("engagement_count") is not None:
                    existing.engagement_delta = (record.get("engagement_count") or 0) - (existing.engagement_count or 0)
                    existing.engagement_count = record.get("engagement_count")
                if record.get("likes") is not None:
                    existing.likes_delta = (record.get("likes") or 0) - (existing.likes or 0)
                    existing.likes = record.get("likes")
                if record.get("comments") is not None:
                    existing.comments_delta = (record.get("comments") or 0) - (existing.comments or 0)
                    existing.comments = record.get("comments")
                if record.get("shares") is not None:
                    existing.shares_delta = (record.get("shares") or 0) - (existing.shares or 0)
                    existing.shares = record.get("shares")
                if record.get("clicks") is not None:
                    existing.clicks_delta = (record.get("clicks") or 0) - (existing.clicks or 0)
                    existing.clicks = record.get("clicks")
                if record.get("engagement_rate") is not None:
                    existing.engagement_rate = record.get("engagement_rate")
                if post_date:
                    existing.post_date = post_date
                existing.metric_date = metric_date
                existing.import_id = record.get("import_id")
                session.add(existing)
            else:
                session.add(
                    PostMetric(
                        user_id=uid,
                        platform_name=platform,
                        import_id=record.get("import_id"),
                        external_url=url,
                        post_date=post_date,
                        impressions=record.get("impressions"),
                        engagement_count=record.get("engagement_count"),
                        engagement_rate=record.get("engagement_rate"),
                        likes=record.get("likes"),
                        comments=record.get("comments"),
                        shares=record.get("shares"),
                        clicks=record.get("clicks"),
                        metric_date=metric_date,
                        impressions_delta=record.get("impressions"),
                        engagement_delta=record.get("engagement_count"),
                        likes_delta=record.get("likes"),
                        comments_delta=record.get("comments"),
                        shares_delta=record.get("shares"),
                        clicks_delta=record.get("clicks"),
                    )
                )

            session.commit()

    def _upsert_daily_metrics_batch(self, records: list[dict]) -> int:
        """Upsert daily metrics by user/platform/date."""
        if not records:
            return 0
        with get_session() as session:
            for record in records:
                metric_date = self._to_date(record.get("metric_date")) or date.today()
                existing = session.exec(
                    select(DailyMetric).where(
                        DailyMetric.user_id == record["user_id"],
                        DailyMetric.platform_name == record["platform_name"],
                        DailyMetric.metric_date == metric_date,
                    )
                ).first()
                if existing:
                    existing.impressions = record.get("impressions")
                    existing.engagements = record.get("engagements")
                    existing.import_id = record.get("import_id")
                    session.add(existing)
                else:
                    session.add(
                        DailyMetric(
                            user_id=record["user_id"],
                            platform_name=record["platform_name"],
                            metric_date=metric_date,
                            impressions=record.get("impressions"),
                            engagements=record.get("engagements"),
                            import_id=record.get("import_id"),
                        )
                    )
            session.commit()
        return len(records)

    def _upsert_follower_metrics_batch(self, records: list[dict]) -> int:
        """Upsert follower metrics by user/platform/date."""
        if not records:
            return 0
        with get_session() as session:
            for record in records:
                metric_date = self._to_date(record.get("metric_date")) or date.today()
                existing = session.exec(
                    select(FollowerMetric).where(
                        FollowerMetric.user_id == record["user_id"],
                        FollowerMetric.platform_name == record["platform_name"],
                        FollowerMetric.metric_date == metric_date,
                    )
                ).first()
                if existing:
                    existing.new_followers = record.get("new_followers")
                    existing.total_followers = record.get("total_followers")
                    existing.import_id = record.get("import_id")
                    session.add(existing)
                else:
                    session.add(
                        FollowerMetric(
                            user_id=record["user_id"],
                            platform_name=record["platform_name"],
                            metric_date=metric_date,
                            new_followers=record.get("new_followers"),
                            total_followers=record.get("total_followers"),
                            import_id=record.get("import_id"),
                        )
                    )
            session.commit()
        return len(records)

    def _upsert_audience_demographics_batch(self, records: list[dict]) -> int:
        """Upsert audience demographics by user/platform/category/value/date."""
        if not records:
            return 0
        with get_session() as session:
            for record in records:
                metric_date = self._to_date(record.get("metric_date"))
                statement = select(AudienceDemographic).where(
                    AudienceDemographic.user_id == record["user_id"],
                    AudienceDemographic.platform_name == record["platform_name"],
                    AudienceDemographic.category == record["category"],
                    AudienceDemographic.value == record["value"],
                )
                if metric_date is None:
                    statement = statement.where(AudienceDemographic.metric_date.is_(None))
                else:
                    statement = statement.where(AudienceDemographic.metric_date == metric_date)
                existing = session.exec(statement).first()
                if existing:
                    existing.percentage = record.get("percentage")
                    existing.import_id = record.get("import_id")
                    existing.metric_date = metric_date
                    session.add(existing)
                else:
                    session.add(
                        AudienceDemographic(
                            user_id=record["user_id"],
                            platform_name=record["platform_name"],
                            category=record["category"],
                            value=record["value"],
                            percentage=record.get("percentage"),
                            import_id=record.get("import_id"),
                            metric_date=metric_date,
                        )
                    )
            session.commit()
        return len(records)

    def _upsert_post_demographics_batch(self, records: list[dict]) -> int:
        """Upsert post demographics by user/platform/url/category/value."""
        if not records:
            return 0
        with get_session() as session:
            for record in records:
                existing = session.exec(
                    select(PostDemographic).where(
                        PostDemographic.user_id == record["user_id"],
                        PostDemographic.platform_name == record["platform_name"],
                        PostDemographic.external_url == record["external_url"],
                        PostDemographic.category == record["category"],
                        PostDemographic.value == record["value"],
                    )
                ).first()
                if existing:
                    existing.percentage = record.get("percentage")
                    existing.import_id = record.get("import_id")
                    session.add(existing)
                else:
                    session.add(
                        PostDemographic(
                            user_id=record["user_id"],
                            platform_name=record["platform_name"],
                            external_url=record["external_url"],
                            category=record["category"],
                            value=record["value"],
                            percentage=record.get("percentage"),
                            import_id=record.get("import_id"),
                        )
                    )
            session.commit()
        return len(records)

    # =========================================================================
    # Query Operations
    # =========================================================================

    def get_imports(self, user_id: Union[str, UUID]) -> list[AnalyticsImportResponse]:
        """Get all imports for a user."""
        uid = self._resolve_user_id(user_id)
        with get_session() as session:
            statement = select(AnalyticsImport).where(
                AnalyticsImport.user_id == uid
            ).order_by(desc(AnalyticsImport.import_date))
            imports = session.exec(statement).all()
            return [
                AnalyticsImportResponse(
                    id=str(i.id),
                    platform_name=i.platform_name,
                    filename=i.filename,
                    import_date=i.import_date.isoformat() if i.import_date else None,
                    row_count=i.row_count,
                    status=i.status,
                    error_message=i.error_message,
                    import_type=i.import_type,
                )
                for i in imports
            ]

    def clear_analytics(self, user_id: Union[str, UUID]) -> dict:
        """Clear all analytics data for a user.

        Returns dict with counts of deleted rows per table.
        """
        uid = self._resolve_user_id(user_id)
        deleted = {}
        with get_session() as session:
            tables = [
                ("post_demographics", PostDemographic),
                ("audience_demographics", AudienceDemographic),
                ("follower_metrics", FollowerMetric),
                ("daily_metrics", DailyMetric),
                ("post_metrics", PostMetric),
                ("analytics_imports", AnalyticsImport),
            ]
            for name, model in tables:
                rows = session.exec(
                    select(model).where(model.user_id == uid)
                ).all()
                deleted[name] = len(rows)
                for row in rows:
                    session.delete(row)
            session.commit()
        return deleted

    def get_metrics(
        self,
        user_id: Union[str, UUID],
        platform_name: Optional[str] = None,
        limit: int = 100,
    ) -> list[PostMetricResponse]:
        """Get metrics for a user."""
        uid = self._resolve_user_id(user_id)
        with get_session() as session:
            statement = select(PostMetric).where(PostMetric.user_id == uid)
            if platform_name:
                statement = statement.where(PostMetric.platform_name == platform_name)
            statement = statement.order_by(desc(PostMetric.metric_date)).limit(limit)
            metrics = session.exec(statement).all()
            return [self._metric_to_response(m) for m in metrics]

    def get_top_posts(
        self,
        user_id: Union[str, UUID],
        metric: str = "impressions",
        limit: int = 10,
    ) -> list[PostMetricResponse]:
        """Get top performing posts."""
        uid = self._resolve_user_id(user_id)
        metric_column = getattr(PostMetric, metric, None)
        if metric_column is None:
            metric_column = PostMetric.impressions
        with get_session() as session:
            statement = (
                select(PostMetric)
                .where(PostMetric.user_id == uid, metric_column.is_not(None))
                .order_by(desc(metric_column))
                .limit(limit)
            )
            metrics = session.exec(statement).all()
            return [self._metric_to_response(m) for m in metrics]

    def get_summary(
        self,
        user_id: Union[str, UUID],
        platform_name: Optional[str] = None,
    ) -> AnalyticsSummary:
        """Get analytics summary for a user."""
        uid = self._resolve_user_id(user_id)
        with get_session() as session:
            statement = select(
                func.count(PostMetric.id),
                func.coalesce(func.sum(PostMetric.impressions), 0),
                func.coalesce(func.sum(PostMetric.engagement_count), 0),
                func.coalesce(func.sum(PostMetric.likes), 0),
                func.coalesce(func.sum(PostMetric.comments), 0),
                func.coalesce(func.sum(PostMetric.shares), 0),
                func.coalesce(func.sum(PostMetric.clicks), 0),
                func.coalesce(func.avg(PostMetric.engagement_rate), 0),
            ).where(PostMetric.user_id == uid)
            if platform_name:
                statement = statement.where(PostMetric.platform_name == platform_name)
            row = session.exec(statement).one()

        top_posts = self.get_top_posts(user_id, "impressions", 5)

        return AnalyticsSummary(
            post_count=row[0],
            total_impressions=row[1],
            total_engagements=row[2],
            total_likes=row[3],
            total_comments=row[4],
            total_shares=row[5],
            total_clicks=row[6],
            avg_engagement_rate=row[7],
            top_posts=top_posts,
        )

    def _metric_to_response(self, m: PostMetric) -> PostMetricResponse:
        """Convert metric record to response."""
        return PostMetricResponse(
            id=str(m.id),
            post_id=str(m.post_id) if m.post_id else None,
            platform_name=m.platform_name,
            external_url=m.external_url,
            post_date=m.post_date.isoformat() if m.post_date else None,
            impressions=m.impressions,
            engagement_count=m.engagement_count,
            engagement_rate=m.engagement_rate,
            likes=m.likes,
            comments=m.comments,
            shares=m.shares,
            clicks=m.clicks,
            metric_date=m.metric_date.isoformat(),
            impressions_delta=m.impressions_delta,
            reactions_delta=m.likes_delta,
        )

    # =========================================================================
    # Daily Metrics Query Operations
    # =========================================================================

    def get_daily_metrics(
        self,
        user_id: Union[str, UUID],
        platform_name: Optional[str] = None,
        limit: int = 90,
    ) -> list[DailyMetricResponse]:
        """Get daily metrics for a user."""
        uid = self._resolve_user_id(user_id)
        with get_session() as session:
            statement = select(DailyMetric).where(DailyMetric.user_id == uid)
            if platform_name:
                statement = statement.where(DailyMetric.platform_name == platform_name)
            statement = statement.order_by(desc(DailyMetric.metric_date)).limit(limit)
            metrics = session.exec(statement).all()
            return [
                DailyMetricResponse(
                    id=str(m.id),
                    platform_name=m.platform_name,
                    metric_date=m.metric_date.isoformat(),
                    impressions=m.impressions,
                    engagements=m.engagements,
                )
                for m in metrics
            ]

    # =========================================================================
    # Follower Metrics Query Operations
    # =========================================================================

    def get_follower_metrics(
        self,
        user_id: Union[str, UUID],
        platform_name: Optional[str] = None,
        limit: int = 90,
    ) -> list[FollowerMetricResponse]:
        """Get follower metrics for a user."""
        uid = self._resolve_user_id(user_id)
        with get_session() as session:
            statement = select(FollowerMetric).where(FollowerMetric.user_id == uid)
            if platform_name:
                statement = statement.where(FollowerMetric.platform_name == platform_name)
            statement = statement.order_by(desc(FollowerMetric.metric_date)).limit(limit)
            metrics = session.exec(statement).all()
            return [
                FollowerMetricResponse(
                    id=str(m.id),
                    platform_name=m.platform_name,
                    metric_date=m.metric_date.isoformat(),
                    new_followers=m.new_followers,
                    total_followers=m.total_followers,
                )
                for m in metrics
            ]

    def get_latest_follower_count(
        self,
        user_id: Union[str, UUID],
        platform_name: str = "linkedin",
    ) -> Optional[int]:
        """Get the most recent total follower count."""
        metrics = self.get_follower_metrics(user_id, platform_name, 1)
        if metrics and metrics[0].total_followers:
            return metrics[0].total_followers
        return None

    # =========================================================================
    # Demographics Query Operations
    # =========================================================================

    def get_audience_demographics(
        self,
        user_id: Union[str, UUID],
        platform_name: Optional[str] = None,
        category: Optional[str] = None,
    ) -> list[AudienceDemographicResponse]:
        """Get audience demographics for a user."""
        uid = self._resolve_user_id(user_id)
        with get_session() as session:
            statement = select(AudienceDemographic).where(AudienceDemographic.user_id == uid)
            if platform_name:
                statement = statement.where(AudienceDemographic.platform_name == platform_name)
            if category:
                statement = statement.where(AudienceDemographic.category == category)
            statement = statement.order_by(desc(AudienceDemographic.percentage))
            demographics = session.exec(statement).all()
            return [
                AudienceDemographicResponse(
                    id=str(d.id),
                    platform_name=d.platform_name,
                    category=d.category,
                    value=d.value,
                    percentage=d.percentage,
                    metric_date=d.metric_date.isoformat() if d.metric_date else None,
                )
                for d in demographics
            ]

    def get_post_demographics(
        self,
        user_id: Union[str, UUID],
        external_url: str,
    ) -> list[PostDemographicResponse]:
        """Get demographics for a specific post."""
        uid = self._resolve_user_id(user_id)
        with get_session() as session:
            statement = select(PostDemographic).where(
                PostDemographic.user_id == uid,
                PostDemographic.external_url == external_url,
            ).order_by(desc(PostDemographic.percentage))
            demographics = session.exec(statement).all()
            return [
                PostDemographicResponse(
                    id=str(d.id),
                    platform_name=d.platform_name,
                    external_url=d.external_url,
                    category=d.category,
                    value=d.value,
                    percentage=d.percentage,
                )
                for d in demographics
            ]
