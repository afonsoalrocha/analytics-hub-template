select audit_delivered_orders_without_items.order_id
from {{ ref('audit_delivered_orders_without_items') }} as audit_delivered_orders_without_items
