# Database Performance Optimizations for Dashboard

# Add these indexes to your migrations
"""
CREATE INDEX CONCURRENTLY idx_beneficiary_status_deleted 
ON social_protection_beneficiary(status, is_deleted) 
WHERE is_deleted = FALSE;

CREATE INDEX CONCURRENTLY idx_individual_gender_family 
ON individual_individual(gender, family_id);

CREATE INDEX CONCURRENTLY idx_beneficiary_created_date 
ON social_protection_beneficiary(created_date DESC) 
WHERE is_deleted = FALSE;

CREATE INDEX CONCURRENTLY idx_location_hierarchy 
ON location_location(parent_id, type);

-- Materialized view for dashboard summary
CREATE MATERIALIZED VIEW dashboard_summary_mv AS
SELECT 
    COUNT(DISTINCT b.id) as total_beneficiaries,
    COUNT(DISTINCT CASE WHEN i.gender = 'M' THEN b.id END) as male_count,
    COUNT(DISTINCT CASE WHEN i.gender = 'F' THEN b.id END) as female_count,
    COUNT(DISTINCT CASE WHEN b.created_date >= CURRENT_DATE - INTERVAL '30 days' THEN b.id END) as recent_enrollments,
    DATE_TRUNC('hour', NOW()) as last_updated
FROM social_protection_beneficiary b
JOIN individual_individual i ON b.individual_id = i.id
WHERE b.is_deleted = FALSE AND b.status = 'ACTIVE';

-- Refresh materialized view (run this periodically)
REFRESH MATERIALIZED VIEW CONCURRENTLY dashboard_summary_mv;
"""

from django.db import models
from django.contrib.postgres.indexes import BrinIndex, GinIndex

class DashboardSummary(models.Model):
    """
    Model for materialized view access
    """
    total_beneficiaries = models.IntegerField()
    male_count = models.IntegerField()
    female_count = models.IntegerField()
    recent_enrollments = models.IntegerField()
    last_updated = models.DateTimeField()
    
    class Meta:
        managed = False
        db_table = 'dashboard_summary_mv'