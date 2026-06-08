import re

with open("frontend/src/app/dashboard/page.tsx", "r") as f:
    content = f.read()

import_statement = "import { useRouter } from \"next/navigation\";\n"
if "import { useRouter }" not in content:
    content = content.replace("import { AnimatePresence, motion } from \"framer-motion\";", "import { AnimatePresence, motion } from \"framer-motion\";\n" + import_statement)

handle_launch = """  const handleLaunchScan = async (repoUrl: string, repoBranch: string) => {
    const job = await runAudit({ repo_url: repoUrl, repo_branch: repoBranch });
    if (job) {
      router.push(`/dashboard/audits/${job.id}`);
    }
  };"""

content = re.sub(
    r'const handleLaunchScan = async \(repoUrl: string, repoBranch: string\) => {.*?};',
    handle_launch,
    content,
    flags=re.DOTALL
)

# Also need to inject router
if "const router = useRouter();" not in content:
    content = re.sub(
        r'export default function Dashboard\(\) {',
        'export default function Dashboard() {\n  const router = useRouter();',
        content
    )

with open("frontend/src/app/dashboard/page.tsx", "w") as f:
    f.write(content)
