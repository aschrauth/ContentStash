# Testing Branch Workflow

## Overview
The `testing` branch has been created to allow testing changes in isolation before deploying to production. This branch serves as a staging environment where features and fixes can be validated before merging to `main`.

## Branch Structure
- **main**: Production-ready code
- **testing**: Pre-production testing environment

## How to Use the Testing Branch

### 1. Switch to the Testing Branch
```bash
git checkout testing
```

### 2. Pull Latest Changes
Always ensure you have the latest testing branch:
```bash
git pull origin testing
```

### 3. Create a Feature Branch from Testing
When working on a new feature or fix:
```bash
git checkout testing
git checkout -b feature/your-feature-name
```

### 4. Make Your Changes
- Develop your feature or fix
- Commit changes regularly with clear messages
- Test locally

### 5. Push Your Feature Branch
```bash
git push -u origin feature/your-feature-name
```

### 6. Create a Pull Request to Testing
- Go to GitHub: https://github.com/aschrauth/ContentStash
- Create a Pull Request from your feature branch to `testing`
- Request code review
- Address any feedback

### 7. Test in the Testing Branch
Once merged to `testing`:
- Deploy to a testing/staging environment
- Perform thorough testing:
  - Functional testing
  - Integration testing
  - User acceptance testing
  - Performance testing
- Verify all features work as expected
- Check for any regressions

### 8. Merge to Main (Production)
After successful testing:
```bash
# Switch to main
git checkout main

# Merge testing into main
git merge testing

# Push to production
git push origin main
```

Or create a Pull Request from `testing` to `main` on GitHub for additional review.

## Best Practices

### Do's ✅
- Always test changes in the `testing` branch before merging to `main`
- Keep the `testing` branch in sync with `main` regularly
- Use descriptive commit messages
- Run all tests before merging
- Document any breaking changes

### Don'ts ❌
- Don't push directly to `main` without testing
- Don't skip testing steps
- Don't merge untested code to `testing`
- Don't leave the `testing` branch too far behind `main`

## Keeping Testing Branch in Sync

Regularly sync `testing` with `main` to avoid conflicts:

```bash
# Switch to testing
git checkout testing

# Pull latest from main
git pull origin main

# Push updated testing branch
git push origin testing
```

## Emergency Hotfixes

For critical production issues:
1. Create a hotfix branch from `main`
2. Fix the issue
3. Test the fix
4. Merge to both `main` and `testing`

```bash
git checkout main
git checkout -b hotfix/critical-issue
# Make fixes
git checkout main
git merge hotfix/critical-issue
git push origin main

git checkout testing
git merge hotfix/critical-issue
git push origin testing
```

## Deployment Workflow

### Testing Environment
- Branch: `testing`
- Purpose: Pre-production validation
- Deploy: After merging feature branches
- URL: [Your testing environment URL]

### Production Environment
- Branch: `main`
- Purpose: Live production
- Deploy: After successful testing
- URL: [Your production URL]

## Troubleshooting

### Merge Conflicts
If you encounter merge conflicts:
```bash
# Resolve conflicts in your editor
git add .
git commit -m "Resolve merge conflicts"
git push
```

### Reverting Changes
If testing reveals issues:
```bash
git checkout testing
git revert <commit-hash>
git push origin testing
```

## Questions?
If you have questions about the testing workflow, please reach out to the team or refer to the project documentation.