"""Single source of truth for image configuration defaults.

This module contains all default scenes, poses, outfits, props, and character
definitions used for seeding new users and as canonical reference data.

Other modules should import from here rather than defining their own copies.
"""

from __future__ import annotations

from typing import TypedDict, Optional


# =============================================================================
# Type Definitions
# =============================================================================


class SceneDefault(TypedDict, total=False):
    """Type definition for a default scene configuration."""
    code: str
    name: str
    viewpoint: str
    desc: str
    is_hardware_only: bool
    no_desk_props: bool


class PoseDefault(TypedDict, total=False):
    """Type definition for a default pose configuration."""
    code: str
    desc: str
    note: str


class OutfitDefault(TypedDict, total=False):
    """Type definition for a default outfit configuration."""
    vest: str
    shirt: str
    pants: str


class PropDefault(TypedDict):
    """Type definition for a default prop configuration."""
    desc: str
    context: str


class CharacterDefault(TypedDict, total=False):
    """Type definition for a default character configuration."""
    appearance: str
    face_details: str
    clothing_rules: Optional[str]


# =============================================================================
# Default Scenes
# =============================================================================

DEFAULT_SCENES: dict[str, list[SceneDefault]] = {
    "SUCCESS": [
        {"code": "A1", "name": "Wide Monitors", "viewpoint": "standard", "desc": "Engineer at desk with multiple monitors. Left monitor: dark editor with colorful syntax highlighting (green, blue, orange text on black). Right monitor: horizontal pipeline diagram with all green checkmarks. Desk has mechanical keyboard, small succulent, notebook. Robot projecting three connected boxes holographically."},
        {"code": "A2", "name": "Terminal Success", "viewpoint": "standard", "desc": "Engineer leaning back satisfied. Terminal showing green text 'BUILD PASSED' on black background, scrolling white log lines above it. Desk has notebooks, pen, headphones. Robot hovering nearby with happy face."},
        {"code": "A3", "name": "Hardware Workbench", "viewpoint": "wide", "desc": "Engineer at workbench with Raspberry Pi (green LED lit), Arduino boards, breadboard with glowing LEDs (green, blue), multimeter showing numbers, soldering iron in stand. Oscilloscope with green waveform in background. Robot scanning a chip with blue beam.", "is_hardware_only": True},
        {"code": "A4", "name": "Over-the-Shoulder Kanban", "viewpoint": "over_shoulder", "desc": "From behind Engineer, physical kanban board with four columns marked by headers. Leftmost column empty, rightmost column full of green sticky notes. Robot placing a card in the rightmost column."},
        {"code": "A5", "name": "Bird's Eye Workstation", "viewpoint": "birds_eye", "desc": "Top-down view of organized desk: ultrawide monitor showing dark code editor with colorful text, mechanical keyboard, mouse, sticky notes with box-and-arrow diagrams, notebook with sketches. Robot hovering above casting soft shadow."},
        {"code": "A6", "name": "Green Pipeline", "viewpoint": "standard", "desc": "Engineer at desk, monitor showing CI/CD pipeline with five stages in a horizontal row, all green checkmarks. Terminal below showing recent deploy logs. Robot projecting a small rocket icon, celebrating successful deployment."},
        {"code": "A7", "name": "Whiteboard Victory", "viewpoint": "wide", "desc": "Engineer at whiteboard with three large boxes connected by arrows left-to-right, labeled 'API', 'SVC', 'DB'. Green checkmarks drawn next to each box. Small flowchart below with diamond decision shape. Robot hovering beside with happy face."},
        {"code": "A8", "name": "Code Review Approval", "viewpoint": "standard", "desc": "Engineer pointing at monitor showing split diff view: left side with red deleted lines, right side with green added lines. Green banner at top. Green +500 and red -200 numbers visible. Chat panel on right with thumbs-up emoji. Robot giving thumbs up."},
        {"code": "A9", "name": "Deploy Success", "viewpoint": "over_shoulder", "desc": "From behind Engineer, dark dashboard on monitor: progress bar at 100% in green, three green circular status dots below, line graph showing flat steady line. Robot celebrating with raised appendages."},
        {"code": "A10", "name": "Documentation Complete", "viewpoint": "standard", "desc": "Engineer at desk, monitor showing clean white page with organized sections, sidebar navigation visible, code block with syntax colors. Physical notebook with bullet-point outline, sticky notes in neat row. Robot projecting checkmark symbol."},
        {"code": "A11", "name": "Pair Programming", "viewpoint": "standard", "desc": "Two monitors side by side. Left: dark editor with colorful code, cursor blinking. Right: terminal with vertical list of green checkmarks, text 'PASS' repeated. Engineer and Robot both focused on screens. Headphones on desk."},
        {"code": "A12", "name": "Morning Standup", "viewpoint": "wide", "desc": "Engineer at standing desk, warm morning light through window. Monitor shows board with columns, rightmost column full of cards. Robot floating at eye level, attentive."},
        {"code": "A13", "name": "System Architecture", "viewpoint": "wide", "desc": "Engineer at whiteboard with five boxes arranged in layers - two on top, three below, connected by arrows pointing down. Each box has green checkmark. Monitor nearby shows terminal with green 'ALL TESTS PASS'. Robot projecting same box diagram holographically."},
        {"code": "A14", "name": "Constraints Working", "viewpoint": "over_shoulder", "desc": "From behind Engineer, monitor showing vertical list with green checkmarks down the left side, each row a single line. Badge icon showing '< 400'. Robot displaying thumbs up. Sticky note with hand-drawn checkmark."},
        {"code": "A15", "name": "Phased Plan Complete", "viewpoint": "over_shoulder", "desc": "From behind Engineer, physical board with four columns. Column headers numbered 1-2-3 and a star. All cards clustered in rightmost star column, other columns empty. Robot placing final card."},
        {"code": "A16", "name": "Template Working", "viewpoint": "standard", "desc": "Engineer at desk, monitor showing form with labeled sections, each section has filled content (colored blocks representing text). Green checkmarks next to each section header. Robot scanning screen with blue beam, approving."},
        {"code": "A17", "name": "Enablement Session", "viewpoint": "wide", "desc": "Engineer at desk, monitor showing presentation slide with large diagram of connected boxes. Second screen shows chat with rows of thumbs-up and heart emoji reactions stacked. Robot displaying lightbulb icon on face."},
        {"code": "A18", "name": "Blast Radius Contained", "viewpoint": "high_angle", "desc": "Camera above looking down at Engineer. Monitor showing diagram of six boxes in a grid, one box highlighted red with dotted border containing it, other five boxes green. Robot showing shield icon on face."},
        {"code": "A19", "name": "Domain Expert Override", "viewpoint": "standard", "desc": "Engineer at desk, left monitor shows code block with red strikethrough line across it. Right monitor shows same code block with green highlighted line. Sticky note with checkmark. Robot looking down, humbled posture."},
        {"code": "A20", "name": "Audit Ready", "viewpoint": "birds_eye", "desc": "Top-down view of desk. Monitor showing dashboard with vertical checklist, all green checkmarks visible. Spreadsheet-like grid next to it, cells filled in. Neat stack of papers, organized sticky notes. Robot hovering above projecting checkmark."},
        {"code": "A21", "name": "Conference Presentation", "viewpoint": "wide", "desc": "Conference room with large screen showing system diagram. Engineer standing at front presenting, gesturing at screen. Three colleagues seated at table, nodding, taking notes. Robot floating beside Engineer, projecting same diagram."},
        {"code": "A22", "name": "Team Huddle Success", "viewpoint": "standard", "desc": "Small group (3-4 people) huddled around standing desk, all looking at shared laptop screen showing green success indicators. Engineer in center explaining. Robot floating above the group, happy face."},
        {"code": "A23", "name": "Before After Split", "viewpoint": "wide", "desc": "Split frame composition. Left half: chaotic desk with scattered papers, tangled cables, red error on screen. Right half: same desk but organized, clean cables, green success on screen. Robot bridging the middle, one half red one half blue."},
        {"code": "A24", "name": "Journey Timeline", "viewpoint": "wide", "desc": "Abstract visualization: winding path from bottom-left to top-right with milestone markers along it (small flags or dots). Engineer standing at the end/top, looking back at path traveled. Robot hovering at final milestone."},
        {"code": "A25", "name": "Control Panel", "viewpoint": "standard", "desc": "Engineer at large dashboard/control panel with organized rows of switches, dials, and indicators - all showing green. Clean, systematic layout. Robot monitoring a section of the panel, displaying thumbs up."},
        {"code": "A26", "name": "Zen Workspace", "viewpoint": "standard", "desc": "Minimalist desk setup: single ultrawide monitor with clean interface, wireless keyboard, one small plant. Everything aligned and orderly. Soft lighting. Engineer in calm posture. Robot hovering peacefully, serene face."},
    ],
    "FAILURE": [
        {"code": "B1", "name": "Build Failed", "viewpoint": "standard", "desc": "Tilted frame. Engineer holding hand up in STOP gesture. Left monitor: terminal with red text 'BUILD FAILED' and white stack trace lines. Right monitor: horizontal pipeline with red X on middle step. Robot recoiling."},
        {"code": "B2", "name": "Tangled Cables", "viewpoint": "close_up", "desc": "Robot tangled in USB cables, ethernet cords, and charging cables. Sparks flying. Engineer's frustrated face visible in soft focus background."},
        {"code": "B3", "name": "Debug Headache", "viewpoint": "close_up", "desc": "Engineer rubbing temples, eyes closed. Terminal showing red error text, indented white lines below (stack trace pattern), line numbers on left margin. Robot hovering nearby looking guilty."},
        {"code": "B4", "name": "Wide Chaos", "viewpoint": "wide", "desc": "Multiple monitors. Left: code with yellow highlighted conflict bands. Middle: vertical list with red X marks. Right: chat bubbles stacking up, red notification badge showing '99+'. Sticky notes scattered everywhere. Engineer spinning chair away. Robot frozen."},
        {"code": "B5", "name": "Bricked Device", "viewpoint": "close_up", "desc": "Camera at desk level. Raspberry Pi with solid red LED (no green), disconnected cables, SD card ejected beside it. Engineer's hands visible palms-up in defeat. Robot crashed on desk, LED face dark/off.", "is_hardware_only": True},
        {"code": "B6", "name": "Split Frame Tension", "viewpoint": "profile", "desc": "Left half shows Engineer's stressed face in profile, bags under eyes, jaw clenched. Right half shows Robot's worried LED face (downturned pixel eyes). Diagonal divide between them. Dramatic side lighting."},
        {"code": "B7", "name": "Facepalm", "viewpoint": "standard", "desc": "Engineer with hand covering face. Monitor behind showing code with one line highlighted yellow, red squiggly underline visible. Sidebar showing file history list. Robot hovering sheepishly."},
        {"code": "B8", "name": "Rollback", "viewpoint": "over_shoulder", "desc": "From behind Engineer frantically typing. Terminal showing white text 'REVERTING...' with progress indicator. Side panel with red toast notifications stacking (3-4 visible). Robot backing away slowly."},
        {"code": "B9", "name": "Production Fire", "viewpoint": "standard", "desc": "Monitor showing dark dashboard with line graph spiking sharply upward in red, red circular alert icons pulsing. Engineer on phone looking stressed, hand running through hair. Robot peeking from behind monitor."},
        {"code": "B10", "name": "Merge Conflict", "viewpoint": "over_shoulder", "desc": "From behind Engineer, monitor showing code with yellow/orange highlighted bands, visible <<<< and >>>> markers in different colors. Sidebar showing branching tree diagram with split paths. Robot with confused face."},
        {"code": "B11", "name": "Infinite Loop", "viewpoint": "standard", "desc": "Terminal showing identical white text lines repeated vertically, scrolling blur effect. Small system monitor widget showing bar graph at 100% red. Motion lines near computer fan. Engineer slumped. Robot displaying spinning dots on face."},
        {"code": "B12", "name": "Wrong Environment", "viewpoint": "close_up", "desc": "Engineer realizing mistake, hand on forehead, wide eyes. Terminal showing red banner with 'PROD' text, table of data rows below. Robot looking nervous with sweat drop icons."},
        {"code": "B13", "name": "Tool Without System", "viewpoint": "wide", "desc": "Engineer frustrated at desk. Monitor shows dashboard with bar charts all near zero, gray empty-state icons. Second screen shows chat with question mark messages. Robot idle, powered but unused, dust particles visible. Branded mug and mousepad unused."},
        {"code": "B14", "name": "No Enablement", "viewpoint": "standard", "desc": "Engineer alone at desk, confused expression. Monitor shows interface with mostly empty panels, no content filled in. Folder icon on desktop labeled with question mark. Robot displaying question mark on face. Sticky note with '???' written."},
        {"code": "B15", "name": "Blast Radius Explosion", "viewpoint": "high_angle", "desc": "Camera above looking down. Multiple monitors showing diagram of boxes, red color spreading from center box to all connected boxes like infection. Engineer holding head with both hands. Robot tangled in drawn arrows, having touched every box."},
        {"code": "B16", "name": "AI Overwrote Everything", "viewpoint": "over_shoulder", "desc": "From behind Engineer staring in horror. Monitor shows diff view that is almost entirely red (deletions), tiny sliver of green. Terminal below shows '47 files changed'. Robot looking guilty, appendages raised."},
        {"code": "B17", "name": "No Checkpoint", "viewpoint": "standard", "desc": "Engineer at desk, monitor showing red error banner at top, stack trace below. Empty sidebar where history/versions would be. Terminal shows red text 'DIRECT TO MAIN'. Robot crashed/tilted on desk. Sticky note with 'skip review' crossed out."},
        {"code": "B18", "name": "Prompt Didnt Scale", "viewpoint": "birds_eye", "desc": "Top-down view of desk covered in sticky notes with arrows connecting them. Monitor shows text editor with tiny font, scroll bar indicating very long document. Output panel shows red 'ERROR'. Robot displaying confused spiral on face."},
        {"code": "B19", "name": "AI Hallucinated", "viewpoint": "standard", "desc": "Engineer pointing at monitor showing code block with one line highlighted red, squiggly underline. Second window showing documentation page with 'NOT FOUND' or '404' visible. Robot sheepish posture, looking away."},
        {"code": "B20", "name": "Garbage In Garbage Out", "viewpoint": "standard", "desc": "Left monitor shows document with sparse bullet points, lots of whitespace (vague input). Right monitor shows dense generated output with a red X overlay. Robot proudly displaying checkmark while Engineer slumps defeated."},
        {"code": "B21", "name": "30 Hours Lost", "viewpoint": "profile", "desc": "Side profile of Engineer slumped at desk, head resting on hand. Clock on wall showing 3:00. Monitor showing code with multiple crossed-out sections visible. Robot powered down, LED face dark."},
        {"code": "B22", "name": "Vendor Demo Skeptic", "viewpoint": "wide", "desc": "Conference room, large screen showing flashy AI dashboard with impressive charts. Vendor presenter animated at front. Engineer seated in audience with skeptical expression, arms crossed. Robot idle/dim in corner, unused."},
        {"code": "B23", "name": "Empty Training Room", "viewpoint": "wide", "desc": "Empty training room with chairs scattered/pushed back. 'AI Workshop' written on whiteboard, half-erased. Projector showing 'Session Cancelled'. Engineer alone at doorway looking at empty room. Robot at front, displaying sad face."},
        {"code": "B24", "name": "Distracted Meeting", "viewpoint": "standard", "desc": "Meeting room, Engineer presenting at screen showing important diagram. Colleagues at table distracted - looking at phones, laptops, side conversations. Robot displaying '...' on face, ignored."},
        {"code": "B25", "name": "Domino Collapse", "viewpoint": "wide", "desc": "Abstract visualization: row of domino blocks falling in chain reaction, spreading outward. Engineer watching helplessly from side, hand reaching out too late. Robot caught in the falling dominoes."},
        {"code": "B26", "name": "Tangled Web", "viewpoint": "standard", "desc": "Large monitor showing complex diagram with too many nodes and crossing lines - impossible to follow. No clear start or end point. Engineer staring overwhelmed. Robot literally tangled in projected lines."},
        {"code": "B27", "name": "Shelfware", "viewpoint": "standard", "desc": "Shelf with dusty software boxes and tools. 'AI Platform' box prominent but covered in dust, never opened. Branded materials faded. Engineer looking at shelf disappointed. Robot covered in cobwebs, powered down."},
        {"code": "B28", "name": "Information Overload", "viewpoint": "high_angle", "desc": "Camera above looking down. Multiple floating/overlapping screens and windows surrounding Engineer, too many to process. Notifications piling up. Engineer hands on head, overwhelmed. Robot spinning, confused spiral on face."},
    ],
    "UNRESOLVED": [
        {"code": "C1", "name": "Empty Coffee Stare", "viewpoint": "standard", "desc": "Engineer holding empty coffee mug, staring at monitor showing code with cursor blinking. Expression distant, thinking. Window shows it's late - dark outside. Robot hovering nearby with amber glow, waiting."},
        {"code": "C2", "name": "Two Terminals", "viewpoint": "standard", "desc": "Engineer looking between two monitors. Left: diagram with many small connected boxes (microservices). Right: diagram with one large box (monolith). Each has a column of + and - bullet points below. Robot displaying scales icon on face."},
        {"code": "C3", "name": "Late Night Debug", "viewpoint": "profile", "desc": "Dark room, Engineer's face lit by single monitor's blue-white glow. Sitting on edge of chair, tired but thinking. Code visible on screen with cursor blinking. Robot hovering low with soft amber glow."},
        {"code": "C4", "name": "Paused Mid-Type", "viewpoint": "close_up", "desc": "Close-up of Engineer's hands hovering above keyboard, frozen mid-thought. Monitor shows half-written code, cursor blinking at end of incomplete line. Robot tilted slightly, also waiting."},
        {"code": "C5", "name": "Monitor Reflection", "viewpoint": "close_up", "desc": "Engineer looking at own reflection in dark/sleeping monitor, screen showing faint 'sleep mode' icon. Robot's amber LED face also visible in the reflection. Second monitor behind shows code with unsaved dot indicator."},
        {"code": "C6", "name": "High Angle Workstation", "viewpoint": "high_angle", "desc": "Camera looking down at Engineer seated at desk. Surrounded by monitors showing various code windows. Sticky notes with hand-drawn '?' marks scattered. Robot hovering above, body curved like question mark shape."},
        {"code": "C7", "name": "Back-to-Back Distance", "viewpoint": "wide", "desc": "Engineer and Robot positioned back-to-back, facing opposite directions. Neither looking at each other. Desk between them with closed laptop, lid down, sleep light pulsing. Emotional distance, muted colors.", "no_desk_props": True},
        {"code": "C8", "name": "Whiteboard Brainstorm", "viewpoint": "wide", "desc": "Engineer staring at whiteboard covered in overlapping diagrams: boxes, arrows going multiple directions, circled items, crossed-out sections, large '?' marks. Robot projecting additional floating boxes, adding to chaos. Analysis paralysis."},
        {"code": "C9", "name": "Documentation Rabbit Hole", "viewpoint": "over_shoulder", "desc": "From behind Engineer, monitor showing browser with 10+ tabs visible at top. Main content shows documentation page with code blocks. Side windows showing forum posts, issue trackers with comment threads. Robot pointing at different tabs, adding confusion."},
        {"code": "C10", "name": "Fork in the Road", "viewpoint": "wide", "desc": "Whiteboard showing Y-shaped fork diagram: one path leading to box labeled 'A', other to box labeled 'B'. Each path has + and - bullet points along it. Engineer chin in hand, marker held loosely. Robot showing animated dots on face (thinking)."},
        {"code": "C11", "name": "Waiting for Review", "viewpoint": "standard", "desc": "Engineer checking phone, slightly bored posture. Monitor showing PR page with yellow 'Pending' status badge, timestamp showing '3 days ago'. Chat panel showing typing indicator dots that never resolve. Robot also waiting, looking at wrist as if checking watch."},
        {"code": "C12", "name": "Refactor Debate", "viewpoint": "standard", "desc": "Monitor showing code with yellow highlighted lines containing 'TODO' and 'FIXME' comments visible. Orange/yellow warning triangles in sidebar gutter. Sticky note with 'Later?' and '?' written. Engineer torn expression. Robot shrugging with appendages out."},
        {"code": "C13", "name": "Constraint Tradeoff", "viewpoint": "wide", "desc": "Whiteboard with T-chart: left column header '+', right column header '-'. Several bullet points in each column. Box at top with word inside. Engineer chin in hand, weighing. Robot showing scales icon. No checkmarks anywhere."},
        {"code": "C14", "name": "Enablement Planning", "viewpoint": "wide", "desc": "Engineer at whiteboard with grid drawn: rows and columns forming training matrix. Some cells filled with checkmarks, others with '?' marks, some empty. Robot hovering, waiting posture, looking at unfilled cells."},
        {"code": "C15", "name": "How Much AI", "viewpoint": "over_shoulder", "desc": "From behind Engineer, whiteboard showing horizontal spectrum line with 'AUTO' on left end, 'MANUAL' on right end. Marker positioned in middle, uncertain. Arrow pointing to middle with '?' above it. Robot waiting beside whiteboard."},
        {"code": "C16", "name": "Expertise Gap", "viewpoint": "over_shoulder", "desc": "From behind Engineer, monitor showing split screen: left side has documentation with technical diagrams, right side has chat window with AI responses that contradict each other (different colored message bubbles). Robot pointing at both sides, confused posture."},
        {"code": "C17", "name": "Human Override Needed", "viewpoint": "standard", "desc": "Monitor showing code suggestion panel with AI-generated code block, yellow question mark icon overlay on it. Engineer paused, hand on chin, eyes narrowed evaluating. Robot in waiting posture, looking at Engineer for verdict."},
        {"code": "C18", "name": "Messy Middle", "viewpoint": "birds_eye", "desc": "Top-down view of physical kanban board. Left 'TODO' column has few cards. Middle 'IN PROGRESS' column is overflowing with cards. Right 'DONE' column is empty. Engineer's hands visible at bottom edge, palms down on table. Robot hovering above middle column, uncertain."},
        {"code": "C19", "name": "Documentation Debt", "viewpoint": "standard", "desc": "Split screen on monitor. Left side: documentation page with old date visible, diagrams that look outdated. Right side: code editor with current code that clearly differs (different structure visible). Engineer pointing at discrepancy between them. Robot pointing at gap."},
        {"code": "C20", "name": "Audit Question", "viewpoint": "high_angle", "desc": "Camera above looking down at Engineer at desk. Monitor showing checklist with some green checkmarks, some yellow question marks, some empty boxes. Spreadsheet visible with some cells highlighted yellow (uncertain). Robot helping scroll through log viewer panel. No clear answer."},
        {"code": "C21", "name": "Abandoned Meeting", "viewpoint": "wide", "desc": "Conference room with half-filled whiteboard, diagrams incomplete. Some chairs pushed back, empty - attendees have left. Engineer alone at table, chin in hand, thinking. Robot hovering by whiteboard, waiting posture, amber glow."},
        {"code": "C22", "name": "Mixed Reception", "viewpoint": "standard", "desc": "Small team huddle (4-5 people) around standing desk. Mixed expressions - some nodding in agreement, some confused with furrowed brows, one shaking head. Engineer in center looking between reactions. Robot displaying scales icon on face."},
        {"code": "C23", "name": "One on One", "viewpoint": "standard", "desc": "Small meeting table, Engineer and one colleague facing each other. Open laptops between them, both screens showing same diagram but different annotations. Body language suggests respectful disagreement. Robot floating between them, neutral posture."},
        {"code": "C24", "name": "Crossroads", "viewpoint": "wide", "desc": "Abstract visualization: Engineer standing at literal fork in path - Y-shaped road. Signposts pointing in different directions with icons (not text). Each path disappearing into fog/uncertainty. Robot hovering at the junction point, looking both ways.", "no_desk_props": True},
        {"code": "C25", "name": "Weighing Options", "viewpoint": "standard", "desc": "Engineer looking at/holding balance scales (physical or projected). Each side has different icons/symbols representing choices. Scales tilting slightly back and forth, not settled. Robot serving as the fulcrum or hovering beside scales."},
        {"code": "C26", "name": "Incomplete Puzzle", "viewpoint": "birds_eye", "desc": "Top-down view of desk with large jigsaw puzzle. Most pieces assembled showing partial picture, but several gaps remain. Loose pieces scattered around edges. Engineer's hand holding one piece, unsure where it fits. Robot pointing at a gap."},
        {"code": "C27", "name": "Spectrum Choice", "viewpoint": "wide", "desc": "Whiteboard or screen showing horizontal gradient/spectrum bar. Left end labeled with one icon, right end with different icon. Marker or pointer positioned in the middle zone. Engineer looking at it, arms crossed, weighing. Robot displaying question mark."},
    ],
}


# =============================================================================
# Default Poses
# =============================================================================

DEFAULT_POSES: dict[str, list[PoseDefault]] = {
    "SUCCESS": [
        {"code": "S1", "desc": "Arms crossed, confident lean against desk or chair", "note": "Ownership, pride"},
        {"code": "S2", "desc": "Seated upright, one hand gesturing toward screen, engaged posture", "note": "Engaged, explaining"},
        {"code": "S3", "desc": "Hands visible, palms open, welcoming gesture", "note": "Transparency, welcome"},
        {"code": "S4", "desc": "Leaning back in chair, hands behind head, relaxed satisfaction", "note": "Relief, satisfaction"},
        {"code": "S5", "desc": "Subtle fist pump or victory gesture", "note": "Celebration, milestone"},
        {"code": "S6", "desc": "Pointing at screen or diagram, teaching posture", "note": "Teaching, showing results"},
        {"code": "S7", "desc": "Coffee mug raised in slight toast gesture", "note": "Quiet celebration"},
        {"code": "S8", "desc": "Thumbs up toward the robot", "note": "Acknowledging the tool"},
        {"code": "S9", "desc": "Writing or sketching on whiteboard, active flow", "note": "Active flow, creating"},
        {"code": "S10", "desc": "Standing, hands on hips, surveying success", "note": "Surveying, accomplished"},
    ],
    "FAILURE": [
        {"code": "F1", "desc": "Rubbing temples with both hands, stress headache", "note": "Stress, headache"},
        {"code": "F2", "desc": "Palms up in shrug gesture, defeat and confusion", "note": "Defeat, confusion"},
        {"code": "F3", "desc": "One hand covering face, regret and disbelief", "note": "Regret, disbelief"},
        {"code": "F4", "desc": "Gripping edge of desk tightly, tension and frustration", "note": "Tension, frustration"},
        {"code": "F5", "desc": "Head in both hands, overwhelmed", "note": "Overwhelmed"},
        {"code": "F6", "desc": "Pinching bridge of nose, exhaustion", "note": "Exhaustion, migraine"},
        {"code": "F7", "desc": "Arms thrown up in exasperation", "note": "Exasperation, giving up"},
        {"code": "F8", "desc": "Slumped in chair, arms hanging, drained", "note": "Drained, defeated"},
        {"code": "F9", "desc": "Hand outstretched in stop gesture, rejecting", "note": "Rejecting, stopping"},
        {"code": "F10", "desc": "Staring at ceiling, seeking patience", "note": "Seeking patience"},
        {"code": "F11", "desc": "Loosening collar, under pressure", "note": "Under pressure, stressed"},
        {"code": "F12", "desc": "Crumpling paper or sticky note, discarding failed attempt", "note": "Discarding, frustrated"},
    ],
    "UNRESOLVED": [
        {"code": "U1", "desc": "Hand on chin, classic thinking pose", "note": "Classic thinking"},
        {"code": "U2", "desc": "Arms crossed, looking away, weighing options", "note": "Weighing, uncertain"},
        {"code": "U3", "desc": "One finger raised, mid-thought, about to speak", "note": "Processing"},
        {"code": "U4", "desc": "Hands clasped, elbows on desk, deliberating", "note": "Deliberating, serious"},
        {"code": "U5", "desc": "Scratching back of head, puzzled", "note": "Puzzled, unsure"},
        {"code": "U6", "desc": "Holding pen to lips, considering options", "note": "Considering options"},
        {"code": "U7", "desc": "Steepled fingers, strategic thinking", "note": "Strategic thinking"},
        {"code": "U8", "desc": "Looking between two objects/screens alternately", "note": "Comparing choices"},
        {"code": "U9", "desc": "Leaning on doorframe, half-turned, hesitating", "note": "Hesitating, paused"},
        {"code": "U10", "desc": "One hand flat on chest, introspective gut-check", "note": "Introspective, gut-check"},
        {"code": "U11", "desc": "Tapping fingers on desk, waiting for clarity", "note": "Waiting, impatient"},
        {"code": "U12", "desc": "Gazing out window, hands in pockets, philosophical", "note": "Philosophical, distant"},
    ],
}


# =============================================================================
# Default Outfits
# =============================================================================

DEFAULT_OUTFITS: list[OutfitDefault] = [
    {"vest": "Navy Blue suit vest", "shirt": "White", "pants": "Dark navy pants"},
    {"vest": "Charcoal Grey suit vest", "shirt": "Light Blue", "pants": "Dark grey pants"},
    {"vest": "Black suit vest", "shirt": "Burgundy", "pants": "Black pants"},
    {"vest": "Tan/Camel suit vest", "shirt": "Navy", "pants": "Dark brown pants"},
    {"vest": "Dark Green suit vest", "shirt": "Floral Print (muted tones)", "pants": "Dark grey pants"},
    {"vest": "Burgundy suit vest", "shirt": "Cream", "pants": "Dark pants"},
]


# =============================================================================
# Default Props
# =============================================================================

DEFAULT_PROPS: dict[str, list[PropDefault]] = {
    "notes": [
        {"desc": "sticky notes with hand-drawn box-and-arrow diagrams", "context": "all"},
        {"desc": "index cards with pseudocode scribbles", "context": "all"},
        {"desc": "sticky notes with state machine drawings", "context": "all"},
        {"desc": "notebook open to a flowchart sketch", "context": "all"},
        {"desc": "sticky note with API endpoint scribbles", "context": "all"},
        {"desc": "notebook with architecture diagram sketch", "context": "all"},
    ],
    "drinks": [
        {"desc": "coffee mug, steam rising", "context": "all"},
        {"desc": "empty espresso cup on saucer", "context": "all"},
        {"desc": "mug with coffee", "context": "all"},
        {"desc": "insulated tumbler", "context": "all"},
        {"desc": "tea mug with tag hanging over edge", "context": "all"},
        {"desc": "cold brew in mason jar", "context": "all"},
    ],
    "tech": [
        {"desc": "mechanical keyboard (professional, no RGB)", "context": "all"},
        {"desc": "USB cables coiled and organized", "context": "all"},
        {"desc": "headphones resting on monitor stand", "context": "all"},
        {"desc": "over-ear headphones on desk", "context": "all"},
        {"desc": "smartphone on desk, screen lit", "context": "all"},
        {"desc": "webcam mounted on monitor", "context": "all"},
        {"desc": "water bottle", "context": "all"},
        {"desc": "laptop closed beside monitor", "context": "all"},
    ],
    "plants": [
        {"desc": "small succulent in geometric planter", "context": "all"},
    ],
    "hardware_boards": [
        {"desc": "Raspberry Pi 4 with ribbon cable to yellow custom PCB nearby", "context": "hardware"},
        {"desc": "Raspberry Pi connected via jumpers to black circuit board with LEDs", "context": "hardware"},
        {"desc": "Raspberry Pi Zero W with yellow prototype board connected by ribbon cable", "context": "hardware"},
        {"desc": "Raspberry Pi with custom HAT stacked on top, status LEDs lit", "context": "hardware"},
        {"desc": "yellow custom PCB with jumper wires running to Raspberry Pi", "context": "hardware"},
        {"desc": "Raspberry Pi 4 beside black circuit board, GPIO ribbon between them", "context": "hardware"},
        {"desc": "Raspberry Pi 5 with colorful jumpers fanning to yellow PCB nearby", "context": "hardware"},
        {"desc": "black custom PCB with exposed traces, ribbon cable to Raspberry Pi", "context": "hardware"},
    ],
    "hardware_tools": [
        {"desc": "multimeter with red and black probes", "context": "hardware"},
        {"desc": "soldering iron resting in brass holder", "context": "hardware"},
        {"desc": "wire strippers and needle-nose pliers", "context": "hardware"},
        {"desc": "oscilloscope probe coiled neatly", "context": "hardware"},
        {"desc": "logic analyzer with colorful clip leads", "context": "hardware"},
        {"desc": "breadboard with jumper wires", "context": "hardware"},
        {"desc": "component tray with resistors and capacitors", "context": "hardware"},
        {"desc": "open notebook with circuit sketches", "context": "hardware"},
        {"desc": "graph paper with timing diagrams", "context": "hardware"},
    ],
}


# =============================================================================
# Default Characters
# =============================================================================

DEFAULT_ENGINEER: CharacterDefault = {
    "appearance": """Male, mid-30s, youthful.
- SKIN: Medium-dark skin, warm olive undertones.
- FACE SHAPE: Broad face, strong jawline, squared chin, fuller cheeks.
- EYEBROWS: Thick dark eyebrows with subtle arch.
- EYES: Large almond-shaped dark brown eyes.
- NOSE: Wide nose with rounded tip.
- LIPS: Full, clearly visible lips with natural color.
- HAIR: Long straight black hair, center-parted, tied back in ponytail.
- FACIAL HAIR: CIRCLE BEARD ONLY (mustache + chin beard connected). CLEAN SHAVEN cheeks/jawline.""",
    "face_details": "Framed from waist up.",
    "clothing_rules": "Vest buttoned up, shirt open collar (NO TIE), sleeves rolled up to forearms, dark pants.",
}

DEFAULT_ROBOT: CharacterDefault = {
    "appearance": """Small hovering robot near the Engineer. Roughly 12 inches diameter.
- Round/oval white metal body with glowing trim (color based on sentiment).
- FACE IS A FLAT SCREEN ONLY: Simple black rectangular display panel showing expression.
- Like an old calculator display. Simple lines/dots only - NO humanoid features.
- Small antenna on top. Floats/hovers, no legs.""",
    "face_details": "Expression changes based on sentiment (happy/distressed/thinking).",
    "clothing_rules": None,
}
