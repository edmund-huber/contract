Simple, type-of-value based contracts for Python, as decorators.

For example, here's a method that takes a string, and returns a
string.

```python
@contract('(str,) -> str')
def exclaim(s):
    return s + '!'
```

Here's a method that takes a string, and returns a method that takes a
string and returns a string.

```python
@contract('(str,) -> (str,) -> str')
def prepender(s):
    @contract('(str,) -> str')
        def wrapper(s2):
            return s + s2
        return wrapper
```