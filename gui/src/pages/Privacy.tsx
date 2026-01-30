export default function Privacy() {
  return (
    <div className="min-h-screen bg-black text-zinc-300 py-12 px-4">
      <div className="max-w-3xl mx-auto">
        <h1 className="text-3xl font-bold text-white mb-8">Privacy Policy</h1>
        <p className="text-sm text-zinc-500 mb-8">Last updated: January 30, 2026</p>

        <div className="space-y-8">
          <section>
            <h2 className="text-xl font-semibold text-white mb-3">1. Introduction</h2>
            <p>
              Postmagiq ("we", "our", or "us") is committed to protecting your privacy.
              This Privacy Policy explains how we collect, use, and safeguard your information
              when you use our AI-powered content creation platform.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-white mb-3">2. Information We Collect</h2>
            <p className="mb-3">We collect the following types of information:</p>
            <ul className="list-disc list-inside space-y-2 ml-4">
              <li><strong>Account Information:</strong> Email address, name, and password when you create an account.</li>
              <li><strong>Content Data:</strong> Text, voice samples, and other content you provide for AI processing.</li>
              <li><strong>Social Media Tokens:</strong> OAuth access tokens when you connect social media accounts (LinkedIn, X, Threads). These are encrypted and used solely to publish content on your behalf.</li>
              <li><strong>Usage Data:</strong> Information about how you use our service, including features accessed and content generated.</li>
            </ul>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-white mb-3">3. How We Use Your Information</h2>
            <ul className="list-disc list-inside space-y-2 ml-4">
              <li>To provide and improve our AI content generation services</li>
              <li>To publish content to your connected social media accounts when you request it</li>
              <li>To analyze your writing samples to learn your voice and style</li>
              <li>To communicate with you about your account and our services</li>
              <li>To ensure the security and integrity of our platform</li>
            </ul>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-white mb-3">4. Social Media Integration</h2>
            <p className="mb-3">
              When you connect social media accounts (LinkedIn, X/Twitter, Threads), we:
            </p>
            <ul className="list-disc list-inside space-y-2 ml-4">
              <li>Store encrypted OAuth tokens to post on your behalf</li>
              <li>Only post content when you explicitly click "Publish"</li>
              <li>Never post without your direct action</li>
              <li>Allow you to disconnect accounts at any time</li>
              <li>Delete your tokens immediately upon disconnection</li>
            </ul>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-white mb-3">5. Data Security</h2>
            <p>
              We implement industry-standard security measures to protect your data:
            </p>
            <ul className="list-disc list-inside space-y-2 ml-4 mt-3">
              <li>All data is encrypted in transit (HTTPS/TLS)</li>
              <li>Social media tokens are encrypted at rest using PostgreSQL pgcrypto</li>
              <li>Passwords are hashed using secure algorithms</li>
              <li>Access to production systems is strictly controlled</li>
            </ul>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-white mb-3">6. Data Retention</h2>
            <p>
              We retain your data for as long as your account is active. You can request
              deletion of your account and all associated data at any time by contacting us
              or using the account deletion feature in Settings.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-white mb-3">7. Third-Party Services</h2>
            <p className="mb-3">We use the following third-party services:</p>
            <ul className="list-disc list-inside space-y-2 ml-4">
              <li><strong>AI Providers:</strong> To generate content (your content is processed but not stored by these providers)</li>
              <li><strong>Payment Processors:</strong> To handle subscription payments securely</li>
              <li><strong>Social Media APIs:</strong> To publish content to your connected accounts</li>
            </ul>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-white mb-3">8. Your Rights</h2>
            <p className="mb-3">You have the right to:</p>
            <ul className="list-disc list-inside space-y-2 ml-4">
              <li>Access your personal data</li>
              <li>Correct inaccurate data</li>
              <li>Delete your account and data</li>
              <li>Export your data</li>
              <li>Disconnect social media accounts at any time</li>
              <li>Opt out of marketing communications</li>
            </ul>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-white mb-3">9. Children's Privacy</h2>
            <p>
              Postmagiq is not intended for users under 18 years of age. We do not knowingly
              collect information from children.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-white mb-3">10. Changes to This Policy</h2>
            <p>
              We may update this Privacy Policy from time to time. We will notify you of any
              material changes by posting the new policy on this page and updating the "Last updated" date.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-white mb-3">11. Contact Us</h2>
            <p>
              If you have questions about this Privacy Policy, please contact us at:{' '}
              <a href="mailto:support@postmagiq.com" className="text-purple-400 hover:text-purple-300">
                support@postmagiq.com
              </a>
            </p>
          </section>
        </div>
      </div>
    </div>
  )
}
