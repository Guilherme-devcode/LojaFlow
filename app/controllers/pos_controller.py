"""POS controller — connects POSView signals to services."""
from app.views.pos.pos_view import POSView


class POSController:
    def __init__(self, view: POSView):
        self._view = view
        view.sale_completed.connect(self._on_sale_completed)

    def _on_sale_completed(self, sale_id: int):
        print(f"[POSController] Sale completed: #{sale_id}")
