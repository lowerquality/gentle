pyinstaller gentle.spec

# For unknown reasons, pyinstaller suddenly started dumping this
# entire root directory into the folder (ie. once I changed the system
# python from homebrew to python.org). This makes zero sense. But in
# lieu of tracking down the bug, let's just go in and delete some of
# the nastier, offending files.
cd dist/gentle.app/Contents/Resources
rm -rf Dockerfile *.sh examples *.spec include lib tests *.pyc gentle *.py *.bkp webdata \
   .git* .travis.yml .DS_Store \
   ext/kaldi ext/*.dSYM ext/Makefile ext/*.cc
cd ../MacOS
rm COPYING Dockerfile *.sh examples *.spec include lib tests *.pyc gentle *.py *.bkp webdata \
   .git* .travis.yml .DS_Store
cd ../../../../

hdiutil create dist/gentle.dmg -volname "Gentle" -srcfolder dist/gentle.app/
