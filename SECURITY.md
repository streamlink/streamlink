# Security policy

We take the security of this project seriously. If you believe you have found a security vulnerability, please report it to us according to the guidelines below.


## Where to report a vulnerability

**Please do not report security vulnerabilities through public GitHub issues, discussions, or pull requests.**

To report a vulnerability privately, use the **GitHub Private Vulnerability Reporting** feature. Navigate to the **Security** tab of this repository on GitHub, select **Advisories**, and click **Report a vulnerability**. This creates a private draft advisory where you can collaborate directly with the maintainers.


## How to report a vulnerability

To keep triage efficient and to ensure maintainer time is focused on fixing actionable vulnerabilities, all reports must adhere to the following criteria:

1. **Proof-of-concept required**  
   Reports containing output from static analysis tools, security scanners, or automated LLMs / AI models will be closed without action unless accompanied by a working, human-verified proof-of-concept demonstrating real-world impact.

2. **Active participation**  
   Security reporters are expected to participate during the triage phase by clarifying findings, confirming reproduction steps, or testing proposed patches on supported environments.

3. **Credit & attribution**  
   Primary reporter credit on associated GHSAs/CVEs is awarded to researchers who actively assist throughout the disclosure process. If a submitter is unable or unwilling to review proposed fixes or answer clarifying technical questions, reporter credit may be withheld or assigned to the maintaining team.


## Preferred information in reports

To help us triage your report quickly, please keep reports **concise, factual, and straight to the point**. Avoid generic security disclaimers, lengthy AI-generated explanations, or unedited tool outputs.

Please focus on the following details:

1. The type of issue
2. The affected versions
3. Step-by-step instructions or code to deterministically reproduce the issue
4. A list of affected components, API endpoints, etc.
5. The potential impact or threat model demonstrating how an attacker could exploit the issue
6. Optionally, any proposed mitigations or patches you've developed yourself


## Disclosure policy

We kindly ask reporters to adhere to responsible disclosure guidelines and keep details private until a public patch is released.

When a valid report is received:

1. Maintainers will confirm the issue and determine affected versions
2. A fix will be developed and verified privately
3. A patched release and a GitHub Security Advisory (with an optional CVE assigned) will be issued simultaneously