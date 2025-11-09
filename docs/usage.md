## 🔧 Setup

1. **Clone this repository**
   ```bash
   git clone https://github.com/<your-username>/<your-repo>.git
   cd <your-repo>/project
   ```

2. **Create and configure `.env` file**
   ```bash
   cp .env.example .env
   # Edit environment variables as needed
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Make CLI executable**
   ```bash
   chmod +x cli.py

---

## 🧠 Usage

### 1. Run CLI directly
```bash
python cli.py --help
```

### 2. Or create a shortcut
Add to your `.zshrc`:
```bash
alias devops="python /path/to/project/cli.py"
```
Then run:
```bash
devops up
```