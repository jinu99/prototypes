#!/bin/bash
# Create a test repository that simulates architecture decay over time
set -e

TEST_DIR="/tmp/decay-test-repo"
rm -rf "$TEST_DIR"
mkdir -p "$TEST_DIR"
cd "$TEST_DIR"
git init
git config user.email "test@example.com"
git config user.name "Test Developer"

# Commit 1: Clean start - two independent modules
mkdir -p src
cat > src/models.py << 'PYEOF'
class User:
    def __init__(self, name):
        self.name = name

class Product:
    def __init__(self, title, price):
        self.title = title
        self.price = price
PYEOF

cat > src/utils.py << 'PYEOF'
import os
import json

def load_config(path):
    with open(path) as f:
        return json.load(f)
PYEOF

git add -A && git commit -m "Initial: clean modules"

# Commit 2: Add a service layer
cat > src/service.py << 'PYEOF'
from src.models import User, Product

class UserService:
    def get_user(self, user_id):
        return User(f"user_{user_id}")

class ProductService:
    def get_product(self, product_id):
        return Product(f"product_{product_id}", 9.99)
PYEOF

git add -A && git commit -m "Add service layer"

# Commit 3: Start introducing coupling
cat > src/models.py << 'PYEOF'
from src.utils import load_config

class User:
    def __init__(self, name):
        self.name = name

class Product:
    def __init__(self, title, price):
        self.title = title
        self.price = price
        self.config = load_config("config.json")
PYEOF

git add -A && git commit -m "Models now depend on utils"

# Commit 4: More coupling + new module
cat > src/api.py << 'PYEOF'
from src.service import UserService, ProductService
from src.models import User
from src.utils import load_config

def handle_request(path):
    config = load_config("api.json")
    us = UserService()
    return us.get_user(1)
PYEOF

git add -A && git commit -m "Add API layer with dependencies"

# Commit 5: Introduce a cyclic dependency
cat > src/utils.py << 'PYEOF'
import os
import json
from src.models import User

def load_config(path):
    with open(path) as f:
        return json.load(f)

def get_default_user():
    return User("default")
PYEOF

git add -A && git commit -m "Utils now imports from models (cycle!)"

# Commit 6: Add a file then delete it (revert pattern)
cat > src/experimental.py << 'PYEOF'
from src.api import handle_request
from src.service import UserService

def experiment():
    return handle_request("/test")
PYEOF

git add -A && git commit -m "Add experimental feature"

# Commit 7: Delete the file (add-delete pattern)
rm src/experimental.py
git add -A && git commit -m "Remove experimental feature"

# Commit 8: Add it back (delete-readd pattern)
cat > src/experimental.py << 'PYEOF'
from src.api import handle_request
from src.service import ProductService
from src.models import Product

def experiment_v2():
    return handle_request("/test/v2")
PYEOF

git add -A && git commit -m "Re-add experimental feature v2"

# Commit 9: More coupling
cat > src/reporting.py << 'PYEOF'
from src.models import User, Product
from src.service import UserService, ProductService
from src.api import handle_request
from src.utils import load_config

class ReportGenerator:
    def generate(self):
        us = UserService()
        ps = ProductService()
        config = load_config("report.json")
        return {"users": 10, "products": 5}
PYEOF

git add -A && git commit -m "Add reporting module with heavy coupling"

# Commit 10: Even more coupling and another cycle
cat > src/service.py << 'PYEOF'
from src.models import User, Product
from src.utils import load_config
from src.reporting import ReportGenerator

class UserService:
    def get_user(self, user_id):
        return User(f"user_{user_id}")

    def get_report(self):
        return ReportGenerator().generate()

class ProductService:
    def get_product(self, product_id):
        config = load_config("products.json")
        return Product(f"product_{product_id}", 9.99)
PYEOF

git add -A && git commit -m "Service depends on reporting (more cycles)"

echo "Test repo created at $TEST_DIR with $(git rev-list --count HEAD) commits"
