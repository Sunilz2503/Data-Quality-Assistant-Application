git init
git add .
git commit -m "Initial commit of Data Quality Assistant"

git remote add origin https://github.com/Sunilz2503/Data-Quality-Assistant-Application.git
git branch -M main
git push -u origin main

npm install gh-pages --save-dev
# OR
yarn add gh-pages --dev

npm run deploy
# OR
yarn deploy