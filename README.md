# Data-Quality-Assistant-Application

git init
git add .
git commit -m "Initial commit of Data Quality Assistant"

git remote add origin <your_repository_url>
git branch -M main
git push -u origin main

npm install gh-pages --save-dev 


{
  "name": "data-quality-assistant",
  "version": "0.1.0",
  "private": true,
  "homepage": "https://<YOUR_GITHUB_USERNAME>.github.io/<YOUR_REPOSITORY_NAME>",
  // ... rest of your package.json
}


{
  // ...
  "scripts": {
    "start": "react-scripts start",
    "build": "react-scripts build",
    "test": "react-scripts test",
    "eject": "react-scripts eject",
    "predeploy": "npm run build", // Or yarn build
    "deploy": "gh-pages -d build"
  },
  // ...
}


npm run deploy
# OR yarn deploy
