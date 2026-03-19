# Commit Guidelines

## Do's and Don'ts

### DO

- Use `git add <specific_files>` to stage only the files you intentionally changed
- Check `git status` and `git diff --staged` before committing
- Write clear, concise commit messages describing what changed and why

### DON'T

- Do NOT use `git add -A` - only add files you explicitly modified
- Do NOT delete or clean up files unless explicitly requested
- Do NOT auto-commit generated files like `uv.lock`, `TODO`, or `.pyc` files
- Do NOT commit changes to unrelated files

### Before Committing

1. Run `git status` to see what files changed
2. Run `git diff` to review your changes
3. Use `git add <file1> <file2>` to stage specific files
4. Use `git diff --staged` to verify staged changes
5. Write a descriptive commit message

### Example Workflow

```bash
git status
git diff
git add specific_file.py another_file.py
git diff --staged
git commit -m "Description of changes"
```
