#!/bin/bash
UPSTREAM_REPO="streamlink"
CLI="streamlink"

usage() {
  echo "This will prepare $CLI for release!"
  echo ""
  echo "Requirements:"
  echo " git"
  echo " gpg - with a valid GPG key already generated"
  echo " hub"
  echo " github-release"
  echo " GITHUB_TOKEN in your env variable"
  echo " "
  echo "Not only that, but you must have permission for:"
  echo " Tagging releases within Github"
  echo ""
}

requirements() {
  if [ ! -f /usr/bin/git ] && [ ! -f /usr/local/bin/git ]; then
    echo "No git. What's wrong with you?"
    return 1
  fi

  if [ ! -f /usr/bin/gpg ] && [ ! -f /usr/local/bin/gpg ]; then
    echo "No gpg. What's wrong with you?"
    return 1
  fi

  if [ ! -f $GOPATH/bin/github-release ]; then
    echo "No $GOPATH/bin/github-release. Please run 'go get -v github.com/aktau/github-release'"
    return 1
  fi

  if [ ! -f /usr/bin/hub ]; then
    echo "No hub. Please run install hub @ github.com/github/hub"
    return 1
  fi

  if [[ -z "$GITHUB_TOKEN" ]]; then
    echo "export GITHUB_TOKEN=yourtoken needed for using github-release"
  fi
}

windows_binary() {
  cd $CLI
  ./script/makeinstaller.sh
  cd ..
  mv $CLI/build/nsis/$CLI-$1.exe .
}

# Clone and then change to user's upstream repo for pushing to master / opening PR's :)
clone() {
  git clone ssh://git@github.com/$UPSTREAM_REPO/$CLI.git
  if [ $? -eq 0 ]; then
        echo OK
  else
        echo FAIL
        exit
  fi
  cd $CLI
  git remote remove origin
  git remote add origin git@github.com:$ORIGIN_REPO/$CLI.git
  git checkout -b release-$1
  cd ..
}

replaceversion() {
  cd $CLI
  OLD_VERSION=`python setup.py --version`
  echo "OLD VERSION:" $OLD_VERSION

  echo "1. Replaced .py versioning"
  find . -name '*.py' -type f -exec sed -i "s/$OLD_VERSION/$1/g" {} \;

  echo "2. Replaced docs versioning"
  find docs/ -name '*.md' -type f -exec sed -i "s/$OLD_VERSION/$1/g" {} \;

  echo "3. Replaced README.md versioning"
  sed -i "s/$OLD_VERSION/$1/g" README.md
  
  cd ..
}

changelog() {
  cd $CLI
  echo "Getting commit changes. Writing to ../changes.txt"
  LOG=`git shortlog --email --no-merges --pretty=%s ${1}..`
  echo -e "\`\`\`\n$LOG\n\`\`\`" > ../changes.txt
  echo "Changelog has been written to changes.txt"
  echo "!!PLEASE REVIEW BEFORE CONTINUING!!"
  echo "Open changes.txt and add the release information"
  echo "to the beginning of the file before the git shortlog"
  cd ..
}

changelog_md() {
  echo "Generating CHANGELOG.md"
  CHANGES=$(cat changes.txt)
  cd $CLI
  DATE=$(date +"%m-%d-%Y")
  CHANGELOG=$(cat CHANGELOG.md)
  HEADER="## $CLI $1 ($DATE)"
  echo -e "$HEADER\n\n$CHANGES\n\n$CHANGELOG" >CHANGELOG.md
  echo "Changes have been written to CHANGELOG.md"
  cd ..
}

git_commit() {
  cd $CLI 

  BRANCH=`git symbolic-ref --short HEAD`
  if [ -z "$BRANCH" ]; then
    echo "Unable to get branch name, is this even a git repo?"
    return 1
  fi
  echo "Branch: " $BRANCH

  git add .
  git commit -m "$1 Release"
  git push origin $BRANCH
  hub pull-request -b $UPSTREAM_REPO/$CLI:master -h $ORIGIN_REPO/$CLI:$BRANCH

  cd ..
  echo ""
  echo "PR opened against master"
  echo ""
}

sign() {
  # Tarball it!
  cp -r $CLI $CLI-$1
  sudo rm -rf $CLI-$1/.git*
  sudo tar czf $CLI-$1.tar.gz $CLI-$1
  if [ $? -eq 0 ]; then
        echo TARBALL OK
  else
        echo TARBALL FAIL
        exit
  fi

  # Sign it!
  echo -e "SIGN THE TARBALL!\n"
  gpg --detach-sign --armor $CLI-$1.tar.gz
  if [ $? -eq 0 ]; then
        echo SIGN OK
  else
        echo SIGN FAIL
        exit
  fi

  echo ""
  echo "The tar.gz. is now located at $CLI-$1.tar.gz"
  echo "and the signed one at $CLI-$1.tar.gz.asc"
  echo ""
}

push() {
  CHANGES=$(cat changes.txt)
  # Release it!
  github-release release \
      --user $UPSTREAM_REPO \
      --repo $CLI \
      --tag $1 \
      --name "$1" \
      --description "$CHANGES"
  if [ $? -eq 0 ]; then
        echo RELEASE UPLOAD OK 
  else 
        echo RELEASE UPLOAD FAIL
        exit
  fi

  github-release upload \
      --user $UPSTREAM_REPO \
      --repo $CLI \
      --tag $1 \
      --name "$CLI-$1.exe" \
      --file $CLI-$1.exe
  if [ $? -eq 0 ]; then
        echo WINDOWS BINARY UPLOAD OK
  else 
        echo WINDOWS BINARY UPLOAD FAIL
        exit
  fi

  github-release upload \
      --user $UPSTREAM_REPO \
      --repo $CLI \
      --tag $1 \
      --name "$CLI-$1.tar.gz" \
      --file $CLI-$1.tar.gz
  if [ $? -eq 0 ]; then
        echo TARBALL UPLOAD OK 
  else 
        echo TARBALL UPLOAD FAIL
        exit
  fi

  github-release upload \
      --user $UPSTREAM_REPO \
      --repo $CLI\
      --tag $1 \
      --name "$CLI-$1.tar.gz.asc" \
      --file $CLI-$1.tar.gz.asc
  if [ $? -eq 0 ]; then
        echo SIGNED TARBALL UPLOAD OK 
  else 
        echo SIGNED TARBALL UPLOAD FAIL
        exit
  fi

  echo "DONE"
  echo "DOUBLE CHECK IT:"
  echo "!!!"
  echo "https://github.com/$UPSTREAM_REPO/$CLI/releases/edit/$1"
  echo "!!!"
  echo "REMEMBER TO UPDATE DOCKER BUILDS! :D"
}

upload_pypi_test() {
  cd $CLI
  python setup.py sdist upload -r pypitest
  cd ..
}

upload_pypi() {
  cd $CLI
  python setup.py sdist upload -r pypi
  cd ..
}

clean() {
  rm -rf $CLI $CLI-$1 $CLI-$1.tar.gz $CLI-$1.tar.gz.asc $CLI-$1.exe changes.txt
}

main() {
  local cmd=$1
  usage

  echo "What is your Github username? (location of your $CLI fork)"
  read ORIGIN_REPO 
  echo "You entered: $ORIGIN_REPO"
  echo ""
  
  echo ""
  echo "First, please enter the version of the NEW release: "
  read VERSION
  echo "You entered: $VERSION"
  echo ""

  echo ""
  echo "Second, please enter the version of the LAST release: "
  read PREV_VERSION
  echo "You entered: $PREV_VERSION"
  echo ""

  clear

  echo "Now! It's time to go through each step of releasing $CLI!"
  echo "If one of these steps fails / does not work, simply re-run ./release.sh"
  echo "Re-enter the information at the beginning and continue on the failed step"
  echo ""

  PS3='Please enter your choice: '
  options=(
  "Git clone master"
  "Replace version number"
  "Generate changelog"
  "Generate changelog for release"
  "Create PR"
  "Tarball and sign - requires gpg key"
  "Create Windows binary"
  "Upload the tarball and Windows binary and push to Github release page"
  "Test upload to pypi"
  "Upload to pypi"
  "Clean"
  "Quit")
  select opt in "${options[@]}"
  do
      echo ""
      case $opt in
          "Git clone master")
              clone $VERSION
              ;;
          "Replace version number")
              replaceversion $VERSION
              ;;
          "Generate changelog")
              changelog $PREV_VERSION
              ;;
          "Generate changelog for release")
              changelog_md $VERSION
              ;;
          "Create PR")
              git_commit $VERSION
              ;;
          "Tarball and sign - requires gpg key")
              sign $VERSION
              ;;
          "Create Windows binary")
              windows_binary $VERSION
              ;;
          "Upload the tarball and Windows binary and push to Github release page")
              push $VERSION
              ;;
          "Test upload to pypi")
              upload_pypi_test
              ;;
          "Upload to pypi")
              upload_pypi
              ;;
          "Clean")
              clean $VERSION
              ;;
          "Quit")
              clear
              break
              ;;
          *) echo invalid option;;
      esac
      echo ""
  done
}

main "$@"
