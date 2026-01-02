"""
Searchable List Mixin
=====================
Provides reusable search/filter functionality for list views.
"""

import flet as ft
from typing import List, Callable, Any, Optional
from ..theme import colors, radius, spacing


class SearchableListMixin:
    """
    Mixin providing search/filter functionality for list views.
    
    Usage:
        class MyView(ft.Container, SearchableListMixin):
            def __init__(self, ...):
                super().__init__(...)
                self._setup_search_mixin()
                
            def _filter_predicate(self, item, query: str) -> bool:
                # Return True if item matches query
                return query.lower() in item.get("name", "").lower()
                
            def _render_list(self):
                # Use self._filtered_items to render
                for item in self._filtered_items:
                    ...
    """
    
    _search_query: str = ""
    _all_items: List[Any] = []
    _filtered_items: List[Any] = []
    _search_field: Optional[ft.TextField] = None
    _debounce_timer: Optional[Any] = None
    
    def _setup_search_mixin(self, debounce_ms: int = 300):
        """
        Initialize the search mixin.
        Call this in __init__ after super().__init__().
        
        Args:
            debounce_ms: Debounce delay for search input (default 300ms)
        """
        self._search_query = ""
        self._all_items = []
        self._filtered_items = []
        self._debounce_ms = debounce_ms
        self._debounce_timer = None
    
    def _create_search_field(
        self,
        placeholder: str = "Search...",
        on_search: Callable[[str], None] = None,
        prefix_icon: str = ft.Icons.SEARCH_ROUNDED,
        expand: bool = True,
        **kwargs
    ) -> ft.TextField:
        """
        Create and return a styled search field.
        """
        import threading
        
        def do_search():
            self._apply_filter()
            if on_search:
                on_search(self._search_query)

        def handle_change(e):
            self._search_query = e.control.value or ""
            
            # Debounce
            if self._debounce_timer:
                self._debounce_timer.cancel()
            
            self._debounce_timer = threading.Timer(0.3, do_search)
            self._debounce_timer.start()
        
        self._search_field = ft.TextField(
            hint_text=placeholder,
            prefix_icon=prefix_icon,
            border_radius=radius.md,
            bgcolor=colors.bg_elevated,
            border_color=colors.glass_border,
            focused_border_color=colors.accent_primary,
            hint_style=ft.TextStyle(color=colors.text_tertiary),
            text_style=ft.TextStyle(color=colors.text_primary),
            expand=expand,
            on_change=handle_change,
            content_padding=ft.padding.symmetric(horizontal=spacing.md, vertical=spacing.sm),
            **kwargs
        )
        
        return self._search_field
    
    def _set_items(self, items: List[Any]):
        """
        Set the full list of items and apply current filter.
        
        Args:
            items: Full list of items to filter
        """
        self._all_items = items or []
        self._apply_filter()
    
    def _apply_filter(self):
        """
        Apply the current search query to filter items.
        Override _filter_predicate to customize filtering logic.
        """
        query = self._search_query.strip().lower()
        
        if not query:
            self._filtered_items = self._all_items.copy()
        else:
            self._filtered_items = [
                item for item in self._all_items 
                if self._filter_predicate(item, query)
            ]
        
        # Call the render method if defined
        if hasattr(self, '_render_list'):
            self._render_list()
    
    def _filter_predicate(self, item: Any, query: str) -> bool:
        """
        Override this method to customize filtering logic.
        
        Args:
            item: The item to check
            query: The lowercase search query
            
        Returns:
            True if item matches the query
        """
        # Default implementation: check common string fields
        if isinstance(item, dict):
            # Check common name fields
            for field in ['displayName', 'name', 'title', 'id']:
                if field in item:
                    if query in str(item[field]).lower():
                        return True
            # Check nested user object
            if 'user' in item and isinstance(item['user'], dict):
                user = item['user']
                if query in user.get('displayName', '').lower():
                    return True
        elif isinstance(item, str):
            return query in item.lower()
        
        return False
    
    def _get_search_stats(self) -> dict:
        """
        Get statistics about the current search.
        
        Returns:
            dict with 'total', 'filtered', and 'query' keys
        """
        return {
            'total': len(self._all_items),
            'filtered': len(self._filtered_items),
            'query': self._search_query,
        }
    
    def _clear_search(self):
        """Clear the search query and show all items."""
        self._search_query = ""
        if self._search_field:
            self._search_field.value = ""
        self._filtered_items = self._all_items.copy()
        
        if hasattr(self, '_render_list'):
            self._render_list()
