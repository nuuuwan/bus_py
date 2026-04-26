class String:
    @staticmethod
    def to_kebab_case(s: str) -> str:
        return s.lower().replace(" ", "-")
