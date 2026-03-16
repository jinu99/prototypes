# Test sample: Python code with AI-generated code smells
# This file demonstrates patterns that ESLint/Pylint typically miss

from abc import ABC, abstractmethod

# ── ACS001: Empty catch/except ──────────────────────────────
# Pylint catches bare `except:` but NOT `except Exception: pass`
def fetch_data(url):
    try:
        import urllib.request
        response = urllib.request.urlopen(url)
        return response.read()
    except Exception:
        pass  # AI silently swallows the error

def process_config(path):
    try:
        with open(path) as f:
            return f.read()
    except FileNotFoundError as e:
        ...  # Another empty pattern AI loves


# ── ACS002: Catch and rethrow ───────────────────────────────
# No traditional linter flags this useless pattern
def validate_input(data):
    try:
        result = complex_validation(data)
        return result
    except ValueError as e:
        raise e  # Pointless: just let it propagate

def another_rethrow():
    try:
        do_something()
    except Exception:
        raise  # Bare re-raise, adds nothing


# ── ACS003: God function ────────────────────────────────────
# Traditional linters check line count OR complexity, not the combo
def process_everything(data, config, options, flags):
    """AI-generated monolith that does way too many things."""
    result = {}
    if data:
        for item in data:
            if item.get("type") == "a":
                for sub in item.get("children", []):
                    if sub.get("active"):
                        try:
                            val = sub["value"]
                            if val > 0:
                                for i in range(val):
                                    if i % 2 == 0:
                                        result[f"a_{i}"] = val * i
                                    else:
                                        result[f"b_{i}"] = val + i
                        except KeyError:
                            pass
            elif item.get("type") == "b":
                for sub in item.get("children", []):
                    if sub.get("active"):
                        try:
                            val = sub["value"]
                            if val > 0:
                                for i in range(val):
                                    if i % 3 == 0:
                                        result[f"c_{i}"] = val * i
                                    else:
                                        result[f"d_{i}"] = val + i
                        except KeyError:
                            pass
            elif item.get("type") == "c":
                for sub in item.get("children", []):
                    if sub.get("active"):
                        try:
                            val = sub["value"]
                            if val > 0:
                                for i in range(val):
                                    if i % 5 == 0:
                                        result[f"e_{i}"] = val * i
                                    else:
                                        result[f"f_{i}"] = val + i
                        except KeyError:
                            pass
    if config:
        if config.get("transform"):
            for key in result:
                if result[key] > 100:
                    result[key] = 100
    return result


# ── ACS004: Hardcoded secrets ───────────────────────────────
# AST-aware: only flags actual assignments, not comments or docs
api_key = "sk-1234567890abcdef"
db_password = "super_secret_123"
jwt_secret = "my-jwt-signing-key-do-not-share"


# ── ACS005: Unnecessary abstraction ────────────────────────
# No linter catches "abstract class with single implementation"
class BaseProcessor(ABC):
    @abstractmethod
    def process(self, data):
        pass

    @abstractmethod
    def validate(self, data):
        pass

class ConcreteProcessor(BaseProcessor):
    def process(self, data):
        return data

    def validate(self, data):
        return True


# Helper stubs
def complex_validation(data):
    return True

def do_something():
    pass
