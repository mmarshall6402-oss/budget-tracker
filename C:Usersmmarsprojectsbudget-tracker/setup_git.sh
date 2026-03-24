#!/bin/bash

# WSL All-in-One GitHub + Project Setup

# 1. Variables
projectFolder=~/projects/budget-tracker
email=mmarshall6402@gmail.com
repoURL=git@github.com:mmarshall6402-oss/budget-tracker.git

# 2. Make project folder
mkdir -p $projectFolder
echo "Project folder: $projectFolder"

# 3. Move Python files from current folder
mv *.py *.json *.html $projectFolder 2>/dev/null
echo "Moved Python project files to $projectFolder"

# 4. Go into project folder
cd $projectFolder

# 5. Generate SSH key if missing
if [ ! -f ~/.ssh/id_ed25519 ]; then
    ssh-keygen -t ed25519 -C $email -f ~/.ssh/id_ed25519 -N ""
    echo "SSH key generated"
else
    echo "SSH key already exists"
fi

# 6. Start SSH agent and add key
eval "$(ssh-agent -s)"
ssh-add ~/.ssh/id_ed25519

# 7. Copy public key to Windows clipboard
cat ~/.ssh/id_ed25519.pub | clip.exe
echo "Public SSH key copied to clipboard. Paste it in GitHub → Settings → SSH keys → New SSH key."

# 8. Initialize Git if needed
if [ ! -d .git ]; then
    git init
    echo "Initialized Git repository"
else
    echo "Git already initialized"
fi

# 9. Add GitHub remote
git remote remove origin 2>/dev/null
git remote add origin $repoURL
echo "GitHub remote set to $repoURL"

# 10. Commit all files
git add .
git commit -m "Initial commit: move existing project files"
echo "Committed project files. Ready to push!"

echo "Next step: Add SSH key to GitHub, then run 'git push -u origin main'"
