# Contributing to Verse Combat Log

First off, thanks for helping Verse Combat Log getting better! 🎉

## 🌟 How Can I Contribute?

### 🐛 Reporting Bugs

Before creating bug reports, please check the [existing issues](../../issues) to avoid duplicates.

When creating a bug report, please include:

- **Clear title and description**
- **Steps to reproduce** the behavior
- **Expected behavior** vs. actual behavior
- **Screenshots** if applicable
- **Environment info**:
  - Star Citizen version (LIVE/PTU/EPTU)
  - Log path
- **Debug logs** (run with `VerseCombatLog.exe --debug` and copy the console output into a file)

**Bug Report Template:**
```markdown
## Description
[Clear description of the bug]

## Steps to Reproduce
1. Go to '...'
2. Click on '...'
3. See error

## Expected Behavior
[What should happen]

## Actual Behavior
[What actually happens]

## Environment
- SC Version: LIVE 4.3.2

## Debug Logs
[Paste relevant logs from --debug mode]
```

### 💡 Suggesting Features

Feature suggestions are welcome! Before suggesting, please:

1. Check if it's already suggested in [Issues](../../issues)
2. Consider if it fits the tool's scope
3. Think about how it benefits the community

**Feature Request Template:**
```markdown
## Feature Description
[Clear description of the feature]

## Use Case
[Why is this feature needed? Who benefits?]

## Proposed Solution
[How could this be implemented?]

## Alternatives
[Are there alternative solutions?]

## Additional Context
[Screenshots, mockups, examples]
```

### 💻 Code Contributions

#### Development Setup

1. **Fork the repository**

2. **Clone your fork**
   ```bash
   git clone https://github.com/yourusername/verse-combat-log.git
   cd verse-combat-log
   ```

3. **Create a virtual environment**
   ```bash
   python -m venv venv
   venv\Scripts\activate  # Windows
   ```

4. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

5. **Run in development mode**
   ```bash
   python app.py --debug
   ```

#### Code Style

- **Python**: Follow [PEP 8](https://pep8.org/)
- **JavaScript**: Use ES6+ features, clear variable names
- **Comments**: Write clear, concise comments in English or German
- **Formatting**: 4 spaces for indentation (Python), 2 spaces (JS/CSS)

#### Commit Messages

Use clear, descriptive commit messages:

```
feat: Add weapon comparison feature
fix: Correct K/D ratio calculation for NPCs
docs: Update installation instructions
style: Format code according to PEP 8
refactor: Optimize log parsing performance
test: Add unit tests for stats_manager
chore: Update dependencies
```

**Format:**
```
<type>: <short description>

[optional body with detailed explanation]

[optional footer with issue references]
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style/formatting (no logic change)
- `refactor`: Code refactoring
- `test`: Adding/updating tests
- `chore`: Maintenance tasks

#### Pull Request Process

1. **Create a branch**
   ```bash
   git checkout -b feature/your-feature-name
   # or
   git checkout -b fix/your-bug-fix
   ```

2. **Make your changes**
   - Write clean, readable code
   - Add comments where necessary
   - Follow existing code style

3. **Test your changes**
   - Test all affected features
   - Ensure no regressions
   - Run with `--debug` to check for errors

4. **Commit your changes**
   ```bash
   git add .
   git commit -m "feat: Add amazing feature"
   ```

5. **Push to your fork**
   ```bash
   git push origin feature/your-feature-name
   ```

6. **Create Pull Request**
   - Go to the original repository
   - Click "New Pull Request"
   - Select your fork and branch
   - Fill in the PR template

**Pull Request Template:**
```markdown
## Description
[Clear description of changes]

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] Tested locally
- [ ] All features still work
- [ ] No console errors

## Screenshots
[If UI changes, add before/after screenshots]

## Checklist
- [ ] Code follows project style
- [ ] Comments added where necessary
- [ ] Documentation updated
- [ ] No breaking changes (or documented)
```

### 🔒 Security Vulnerabilities

**DO NOT** create public issues for security vulnerabilities.

Instead, please report them privately:
- Email: [vcl@sebo.one]
- Or create a private security advisory on GitHub

## 📋 Project Structure

```
verse-combat-log/
├── app.py                 # Main Flask application
├── log_parser.py          # Game.log parser
├── stats_manager.py       # Statistics management
├── config_manager.py      # Configuration management
├── weapon_database.py     # Weapon name management
├── vehicle_database.py    # Vehicle name management
├── player_database.py     # Player data storage
├── names_parser.py        # INI file parser
├── ini_updater.py         # Auto-update system
├── filter_ini.py          # INI conversion utility
│
├── templates/             # HTML templates
│   ├── index.html
│   └── loading.html
│
├── static/                # Frontend assets
│   ├── css/
│   │   └── style.css
│   ├── js/
│   │   └── app.js
│   └── media/             # Images & logos
│
├── build_exe.spec         # PyInstaller build config
├── requirements.txt       # Python dependencies
└── README.md             # Project documentation
```

## 🎯 Development Guidelines

### Python Backend

- **Type Hints**: Use type hints where possible
- **Error Handling**: Always handle exceptions gracefully
- **Logging**: Use `print()` for important events (visible in debug mode)
- **Performance**: Consider performance for log parsing (runs frequently)

### JavaScript Frontend

- **Modern JS**: Use ES6+ features (const/let, arrow functions, etc.)
- **No jQuery**: Vanilla JavaScript only
- **WebSocket**: Use SocketIO for real-time updates
- **DOM Manipulation**: Minimize reflows/repaints

### UI/UX

- **Dark Theme**: Maintain consistent dark theme
- **Responsive**: Ensure UI works at 1024x768 minimum
- **Accessibility**: Consider color contrast, text size
- **Feedback**: Provide visual feedback for user actions

## ✅ Testing Checklist

Before submitting a PR, test:

- [ ] Tool starts without errors
- [ ] All tabs load correctly
- [ ] Session stats update in real-time
- [ ] Total stats persist after restart
- [ ] Player profiles load
- [ ] Settings save correctly
- [ ] Version switching works
- [ ] No console errors (check with F12)
- [ ] Works with `--debug` flag
- [ ] EXE builds successfully (if applicable)

## 📞 Getting Help

Need help with development?

- **Issues**: Create an issue with `question` label
- **Discussions**: Use GitHub Discussions for general questions

## 📜 Code of Conduct

### Our Pledge

We pledge to make participation in our project a harassment-free experience for everyone.

### Our Standards

**Positive behavior:**
- Being respectful and inclusive
- Accepting constructive criticism
- Focusing on what's best for the community
- Showing empathy

**Unacceptable behavior:**
- Harassment or discriminatory language
- Trolling or insulting comments
- Personal or political attacks
- Publishing others' private information

### Enforcement

Project maintainers have the right to remove, edit, or reject contributions that don't align with this Code of Conduct.

## 📄 License

By contributing, you agree that your contributions will be licensed under the **Creative Commons Attribution-NonCommercial 4.0 International License** (CC BY-NC 4.0).

This means:
- ✅ Your contributions can be freely shared and adapted
- 📝 With proper attribution
- 🚫 But not for commercial purposes

See [LICENSE](LICENSE) file for full details.

---

## 🙏 Thank You!

Your contributions, big or small, make a difference!

**o7 Citizens! Happy coding!**
