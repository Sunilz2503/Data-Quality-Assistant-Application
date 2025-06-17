# Beginner’s Guide: Deploy Your React App to GitHub Pages

## 1. Create a GitHub Account

Go to [github.com](https://github.com/) and sign up for a free account.

![GitHub Signup Page](https://docs.github.com/assets/images/help/profile/signup.png)

---

## 2. Create a New Repository

1. Click the **+** icon in the upper-right, then select **New repository**.

   ![New Repository](https://docs.github.com/assets/images/help/repository/repo-create.png)

2. Enter a repository name (e.g., `Data-Quality-Assistant-Application`), add a description, select **Public**, and click **Create repository**.

   ![Repository Details](https://docs.github.com/assets/images/help/repository/create-repository-name.png)

---

## 3. Set Up Git Locally and Add Your Project

### Open your terminal and run:

```bash
git init
git remote add origin https://github.com/Sunilz2503/Data-Quality-Assistant-Application.git
```

### Add and Commit Your Code

```bash
git add .
git commit -m "Initial commit"
git push -u origin main
```

---

## 4. Install gh-pages and Prepare Your React App

### Install gh-pages

```bash
npm install --save-dev gh-pages
```

### Update your `package.json`:

Add a `homepage` field:

```json
"homepage": "https://Sunilz2503.github.io/Data-Quality-Assistant-Application"
```

Add deploy scripts:

```json
"scripts": {
  "predeploy": "npm run build",
  "deploy": "gh-pages -d build"
}
```

---

## 5. Deploy to GitHub Pages

### Deploy!

```bash
npm run deploy
```

---

## 6. Enable GitHub Pages

1. Go to your repository on GitHub.
2. Click **Settings** > **Pages**.
3. Under **Source**, select the `gh-pages` branch and click **Save**.

   ![GitHub Pages Settings](https://docs.github.com/assets/images/help/pages/pages-source-settings.png)

---

## 7. Visit Your Site

Go to:  
```
https://Sunilz2503.github.io/Data-Quality-Assistant-Application
```

Your React app is live!

---

## More Resources

- [GitHub Docs - Getting Started](https://docs.github.com/en/get-started)
- [Create React App Deployment](https://create-react-app.dev/docs/deployment/#github-pages)

---

Congratulations! 🎉 You’ve deployed your first React app to GitHub Pages.
