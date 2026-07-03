class CacheKeys:
    @staticmethod
    def product_list(
        business_id: str, page: int, limit: int,
        search: str = "", category: str = "", low_stock: bool = False,
    ) -> str:
        filter_hash = f"{search}:{category}:{low_stock}"
        return f"smarta:{business_id}:products:list:{page}:{limit}:{filter_hash}"

    @staticmethod
    def product_detail(business_id: str, product_id: str) -> str:
        return f"smarta:{business_id}:products:detail:{product_id}"

    @staticmethod
    def product_pattern(business_id: str) -> str:
        return f"smarta:{business_id}:products:*"

    @staticmethod
    def sales_report(business_id: str, period: str) -> str:
        return f"smarta:{business_id}:reports:sales:{period}"

    # Unused until business settings endpoint exists — do not cache-populate
    # without a corresponding invalidation path.
    @staticmethod
    def business_settings(business_id: str) -> str:
        return f"smarta:{business_id}:settings"

    @staticmethod
    def token_blacklist(jti: str) -> str:
        return f"smarta:session:blacklist:{jti}"

    @staticmethod
    def user_profile(user_id: str) -> str:
        return f"smarta:user:{user_id}:profile"
