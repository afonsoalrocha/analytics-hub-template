select mart_monthly_commerce.purchase_month
from {{ ref('mart_monthly_commerce') }} as mart_monthly_commerce
where
    mart_monthly_commerce.delivered_orders <= 0
    or mart_monthly_commerce.product_revenue < 0
    or mart_monthly_commerce.average_ticket < 0
