class DFSCursor:
    def __init__(self, root):
        self.stack = [root]

    def next(self):
        if not self.stack:
            return None
        
        node = self.stack.pop()

        for child in reversed(node["children"]):
            self.stack.append(child)

        return node

    def peek(self):
        if not self.stack:
            return None
        return self.stack[-1]   