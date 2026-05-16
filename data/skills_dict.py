"""
skills_dict.py
--------------
Predefined, category-wise technical skills dictionary for resume parsing.

Structure:
    SKILLS_DICT: dict[category: str, list[str]]
        Each category maps to a list of canonical skill names (lowercase).
        Aliases and alternate spellings are handled in skill_extractor.py.

Design decisions:
    - All entries are lowercase to simplify case-insensitive matching.
    - Multi-word skills are stored as-is (e.g., "machine learning").
      The extractor normalises the resume text before matching.
    - Versioned variants (python 3, es6) are excluded; only the base name
      is stored here. Version extraction can be added as a future layer.
    - Categories mirror common recruiter / ATS groupings.
"""

SKILLS_DICT: dict[str, list[str]] = {

    # ── Programming Languages ──────────────────────────────────────────────
    "programming_languages": [
        "python", "javascript", "typescript", "java", "c", "c++", "c#",
        "go", "golang", "rust", "swift", "kotlin", "scala", "ruby",
        "php", "r", "matlab", "perl", "dart", "lua", "haskell",
        "elixir", "erlang", "clojure", "f#", "bash", "shell",
        "powershell", "assembly", "fortran", "cobol",
    ],

    # ── Web – Frontend ─────────────────────────────────────────────────────
    "frontend": [
        "html", "css", "react", "react.js", "next.js", "vue", "vue.js",
        "nuxt", "angular", "svelte", "sveltekit", "jquery", "bootstrap",
        "tailwind", "tailwindcss", "sass", "scss", "less", "webpack",
        "vite", "parcel", "rollup", "babel", "redux", "zustand",
        "recoil", "mobx", "graphql", "apollo", "storybook",
        "three.js", "react three fiber", "framer motion",
        "web components", "pwa", "service workers",
    ],

    # ── Web – Backend ──────────────────────────────────────────────────────
    "backend": [
        "node.js", "express", "express.js", "fastapi", "flask",
        "django", "spring", "spring boot", "asp.net", "rails",
        "ruby on rails", "laravel", "gin", "fiber", "nestjs",
        "hapi", "koa", "strapi", "fastify", "rest api", "graphql",
        "grpc", "websocket", "socket.io",
    ],

    # ── Databases ──────────────────────────────────────────────────────────
    "databases": [
        "mysql", "postgresql", "postgres", "sqlite", "mongodb",
        "redis", "cassandra", "dynamodb", "firebase",
        "firestore", "neo4j", "elasticsearch", "mariadb",
        "cockroachdb", "supabase", "planetscale", "oracle",
        "ms sql", "sql server", "influxdb",
    ],

    # ── Cloud & DevOps ─────────────────────────────────────────────────────
    "cloud_devops": [
        "aws", "gcp", "azure", "docker", "kubernetes", "k8s",
        "terraform", "ansible", "jenkins", "github actions",
        "gitlab ci", "circleci", "helm", "nginx", "apache",
        "linux", "ubuntu", "centos", "debian",
        "cloudflare", "vercel", "netlify", "render", "heroku",
        "ci/cd", "devops", "infrastructure as code",
        "load balancing", "cdn",
    ],

    # ── Mobile ─────────────────────────────────────────────────────────────
    "mobile": [
        "android", "ios", "swift", "swiftui", "kotlin",
        "react native", "flutter", "dart", "xcode",
        "android studio", "expo", "jetpack compose",
    ],

    # ── Machine Learning & Data Science ───────────────────────────────────
    "ml_data_science": [
        "machine learning", "deep learning", "neural networks",
        "natural language processing", "nlp", "computer vision",
        "scikit-learn", "sklearn", "tensorflow", "keras",
        "pytorch", "xgboost", "lightgbm", "catboost",
        "pandas", "numpy", "matplotlib", "seaborn", "plotly",
        "jupyter", "scipy", "statsmodels", "hugging face",
        "transformers", "llm", "langchain", "openai api",
        "feature engineering", "data preprocessing",
        "model deployment", "mlops", "data analysis",
        "data visualization", "time series", "regression",
        "classification", "clustering",
    ],

    # ── Tools & Platforms ──────────────────────────────────────────────────
    "tools_platforms": [
        "git", "github", "gitlab", "bitbucket",
        "jira", "confluence", "notion", "trello",
        "figma", "postman", "swagger", "insomnia",
        "vs code", "intellij", "pycharm", "xcode",
        "vim", "neovim", "linux terminal",
    ],

    # ── Security ───────────────────────────────────────────────────────────
    "security": [
        "oauth", "oauth2", "jwt", "ssl", "tls", "https",
        "cors", "csrf", "xss", "sql injection", "penetration testing",
        "cryptography", "hashing", "bcrypt", "auth0",
        "firebase auth", "keycloak", "ldap",
    ],

    # ── System Design & Architecture ──────────────────────────────────────
    "system_design": [
        "system design", "microservices", "monolith",
        "event-driven architecture", "message queues",
        "rabbitmq", "kafka", "pubsub", "celery",
        "caching", "load balancer", "api gateway",
        "distributed systems", "scalability", "high availability",
        "design patterns", "solid principles", "mvc", "mvvm",
    ],

    # ── DSA & CS Fundamentals ──────────────────────────────────────────────
    "dsa_fundamentals": [
        "data structures", "algorithms", "linked list", "binary tree",
        "graph", "dynamic programming", "greedy", "backtracking",
        "sorting", "searching", "complexity analysis", "big o notation",
        "recursion", "stack", "queue", "heap", "hash map", "trie",
    ],

    # ── Testing ────────────────────────────────────────────────────────────
    "testing": [
        "unit testing", "integration testing", "e2e testing",
        "jest", "mocha", "chai", "pytest", "unittest",
        "cypress", "playwright", "selenium", "postman",
        "test driven development", "tdd", "bdd",
    ],

    # ── APIs & Integrations ────────────────────────────────────────────────
    "apis_integrations": [
        "rest", "restful", "rest api", "graphql", "grpc",
        "webhook", "razorpay", "stripe", "twilio",
        "sendgrid", "firebase", "google maps api",
        "openai", "anthropic", "groq", "hugging face api",
        "github api", "twitter api", "slack api",
    ],

    # ── Soft Skills (optional – can be disabled) ───────────────────────────
    "soft_skills": [
        "teamwork", "communication", "leadership", "problem solving",
        "critical thinking", "time management", "agile", "scrum",
        "collaboration", "presentation", "mentoring",
    ],
}

# ── Alias Map ──────────────────────────────────────────────────────────────
# Maps non-canonical surface forms → canonical skill name.
# The extractor resolves these before deduplication.
ALIASES: dict[str, str] = {
    # Language aliases
    "js":               "javascript",
    "ts":               "typescript",
    "py":               "python",
    "cpp":              "c++",
    "csharp":           "c#",

    # Framework aliases
    "reactjs":          "react",
    "react js":         "react",
    "nextjs":           "next.js",
    "next js":          "next.js",
    "vuejs":            "vue",
    "vue js":           "vue",
    "nodejs":           "node.js",
    "node js":          "node.js",
    "expressjs":        "express",
    "express js":       "express",

    # DB aliases
    "mongo":            "mongodb",
    "postgres":         "postgresql",
    "psql":             "postgresql",
    "mssql":            "ms sql",

    # Cloud aliases
    "amazon web services": "aws",
    "google cloud":     "gcp",
    "google cloud platform": "gcp",
    "microsoft azure":  "azure",

    # Tool aliases
    "vscode":           "vs code",
    "visual studio code": "vs code",

    # ML aliases
    "sk-learn":         "scikit-learn",
    "sklearn":          "scikit-learn",
    "hf":               "hugging face",
    "open ai":          "openai api",
    "gpt":              "openai api",

    # Misc
    "k8":               "kubernetes",
    "gh actions":       "github actions",
    "ci cd":            "ci/cd",
    "cicd":             "ci/cd",
    "tdd":              "test driven development",
    "nlp":              "natural language processing",
    "ml":               "machine learning",
    "dl":               "deep learning",
    "cv":               "computer vision",
}

# ── Categories to skip during extraction (toggle off noisy categories) ────
EXCLUDED_CATEGORIES: set[str] = set()
# Example: EXCLUDED_CATEGORIES = {"soft_skills"}