# 🚀 Page Picks NFL Analytics - Deployment Guide

## Quick Deploy to Railway (Recommended)

### Step 1: Prepare Your Code
1. Make sure all files are in your project folder
2. The following files are already created for you:
   - `Procfile` - Tells Railway how to run your app
   - `railway.json` - Railway configuration
   - `runtime.txt` - Python version
   - `requirements.txt` - Dependencies

### Step 2: Create GitHub Repository
1. Go to [GitHub.com](https://github.com) and create a new repository
2. Name it something like `page-picks-nfl`
3. Make it public (required for free Railway deployment)
4. Upload all your project files to the repository

### Step 3: Deploy to Railway
1. Go to [Railway.app](https://railway.app)
2. Sign up with your GitHub account
3. Click "New Project"
4. Select "Deploy from GitHub repo"
5. Choose your `page-picks-nfl` repository
6. Railway will automatically detect it's a Python app
7. Click "Deploy"

### Step 4: Configure Environment
1. In Railway dashboard, go to your project
2. Click on the service
3. Go to "Variables" tab
4. Add any environment variables if needed
5. The app will automatically restart with new settings

### Step 5: Access Your Website
1. Railway will give you a URL like `https://your-app-name.railway.app`
2. Your NFL analytics will be live at that URL!
3. The demo page will be at `https://your-app-name.railway.app/demo`

## Alternative: Deploy to Render

### Step 1: Create Render Account
1. Go to [Render.com](https://render.com)
2. Sign up with GitHub

### Step 2: Deploy
1. Click "New +" → "Web Service"
2. Connect your GitHub repository
3. Use these settings:
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn working_api:app --host 0.0.0.0 --port $PORT`
4. Click "Create Web Service"

## Alternative: Deploy to Vercel

### Step 1: Install Vercel CLI
```bash
npm i -g vercel
```

### Step 2: Deploy
```bash
vercel --prod
```

## Database Considerations

### For Production:
- Railway provides PostgreSQL database add-ons
- Render has built-in database support
- Consider migrating from SQLite to PostgreSQL for production

### Current Setup:
- Your app currently uses SQLite (file-based database)
- This works for small to medium traffic
- For high traffic, consider upgrading to PostgreSQL

## Custom Domain (Optional)

### Railway:
1. Go to your project settings
2. Click "Domains"
3. Add your custom domain
4. Update DNS records as instructed

### Render:
1. Go to your service settings
2. Click "Custom Domains"
3. Add your domain
4. Follow DNS setup instructions

## Monitoring & Updates

### Automatic Updates:
- Push changes to GitHub
- Railway/Render will automatically redeploy
- Your website will update automatically

### Manual Updates:
- Use the `update_2025_and_injuries.py` script
- Run it locally and push changes
- Or set up scheduled updates (advanced)

## Troubleshooting

### Common Issues:
1. **Build Fails**: Check `requirements.txt` has all dependencies
2. **App Won't Start**: Check `Procfile` and start command
3. **Database Issues**: Ensure database file is included in repository
4. **Port Issues**: Make sure app uses `$PORT` environment variable

### Getting Help:
- Check Railway/Render logs in dashboard
- Test locally first with `python working_api.py`
- Check that all files are in the repository

## Cost

### Free Tiers:
- **Railway**: 500 hours/month free
- **Render**: 750 hours/month free
- **Vercel**: Unlimited for static sites

### Paid Plans:
- Start around $5-10/month for more resources
- Only needed if you get high traffic

---

## 🎉 You're Ready!

Once deployed, your NFL analytics will be live on the web! Share the URL with friends and start making picks! 🏈
