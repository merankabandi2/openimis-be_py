"""
Optimized queries for JSON fields in PostgreSQL
"""
from django.db import connection
from django.core.cache import cache
from django.db.models import Q, Count, Avg, Sum, F
from django.contrib.postgres.fields import JSONField
from django.db.models.expressions import RawSQL
import json

class DashboardJSONQueries:
    """
    Optimized queries for dashboard data from JSON fields
    """
    
    @staticmethod
    def get_household_statistics():
        """
        Get household statistics from group JSON data
        """
        cache_key = 'dashboard_household_stats'
        cached = cache.get(cache_key)
        if cached:
            return cached
        
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    -- Total households
                    COUNT(*) as total_households,
                    
                    -- Household types
                    COUNT(*) FILTER (WHERE Json_ext->>'type_menage' = 'TYPE_MENAGE_DEUX_PARENTS') as two_parent_households,
                    COUNT(*) FILTER (WHERE Json_ext->>'type_menage' = 'TYPE_MENAGE_MONOPARENTAL') as single_parent_households,
                    
                    -- Vulnerability status
                    COUNT(*) FILTER (WHERE Json_ext->>'vulnerable_ressenti' = 'VULNERABILITE_RESSENTI_OUI') as vulnerable_households,
                    COUNT(*) FILTER (WHERE Json_ext->>'menage_mutwa' = 'OUI') as twa_households,
                    COUNT(*) FILTER (WHERE Json_ext->>'menage_refugie' = 'OUI') as refugee_households,
                    COUNT(*) FILTER (WHERE Json_ext->>'menage_deplace' = 'OUI') as displaced_households,
                    COUNT(*) FILTER (WHERE Json_ext->>'menage_rapatrie' = 'OUI') as repatriated_households,
                    
                    -- Living conditions
                    AVG(CAST(NULLIF(Json_ext->>'logement_pieces', '') AS FLOAT)) as avg_rooms,
                    COUNT(*) FILTER (WHERE Json_ext->>'logement_electricite_a' = 'OUI') as with_electricity,
                    COUNT(*) FILTER (WHERE Json_ext->>'logement_eau_boisson' = 'LOGEMENT_EAU_BOISSON_ROBINET') as with_tap_water,
                    
                    -- Economic indicators
                    COUNT(*) FILTER (WHERE Json_ext->>'a_terres' = 'OUI') as with_land,
                    COUNT(*) FILTER (WHERE Json_ext->>'a_elevage' = 'OUI') as with_livestock,
                    AVG(CAST(NULLIF(Json_ext->>'score_pmt_initial', '') AS FLOAT)) as avg_pmt_score,
                    
                    -- Food security
                    COUNT(*) FILTER (WHERE Json_ext->>'alimentaire_sans_nourriture' = 'ALIMENTAIRE_SANS_NOURRITURE_OUI') as food_insecure,
                    AVG(CAST(NULLIF(Json_ext->>'alimentaire_num_repas_adultes', '') AS FLOAT)) as avg_meals_adults,
                    
                    -- Assets
                    AVG(CAST(NULLIF(Json_ext->>'possessions_houe', '0') AS FLOAT)) as avg_hoes,
                    COUNT(*) FILTER (WHERE CAST(NULLIF(Json_ext->>'possessions_radio', '') AS INT) > 0) as with_radio,
                    COUNT(*) FILTER (WHERE CAST(NULLIF(Json_ext->>'possessions_smartphone', '') AS INT) > 0) as with_smartphone,
                    COUNT(*) FILTER (WHERE CAST(NULLIF(Json_ext->>'possessions_velo', '') AS INT) > 0) as with_bicycle,
                    
                    -- Location distribution
                    COUNT(DISTINCT Json_ext->>'province_code') as provinces_count,
                    COUNT(DISTINCT Json_ext->>'commune_code') as communes_count
                    
                FROM individual_group
                WHERE "isDeleted" = false
                AND Json_ext->>'etat' = 'INSCRIT'
            """)
            
            columns = [col[0] for col in cursor.description]
            result = dict(zip(columns, cursor.fetchone()))
            
            # Cache for 1 hour
            cache.set(cache_key, result, 3600)
            return result
    
    @staticmethod
    def get_individual_demographics():
        """
        Get individual demographics from JSON data
        """
        cache_key = 'dashboard_individual_demographics'
        cached = cache.get(cache_key)
        if cached:
            return cached
        
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    -- Total individuals
                    COUNT(*) as total_individuals,
                    
                    -- Gender distribution
                    COUNT(*) FILTER (WHERE Json_ext->>'sexe' = 'M') as male_count,
                    COUNT(*) FILTER (WHERE Json_ext->>'sexe' = 'F') as female_count,
                    
                    -- Age groups (calculated from dob)
                    COUNT(*) FILTER (WHERE AGE(dob) < INTERVAL '5 years') as age_0_5,
                    COUNT(*) FILTER (WHERE AGE(dob) >= INTERVAL '5 years' AND AGE(dob) < INTERVAL '18 years') as age_5_18,
                    COUNT(*) FILTER (WHERE AGE(dob) >= INTERVAL '18 years' AND AGE(dob) < INTERVAL '60 years') as age_18_60,
                    COUNT(*) FILTER (WHERE AGE(dob) >= INTERVAL '60 years') as age_60_plus,
                    
                    -- Education
                    COUNT(*) FILTER (WHERE Json_ext->>'va_ecole' = 'OUI') as attending_school,
                    COUNT(*) FILTER (WHERE Json_ext->>'lit' = 'OUI') as literate,
                    COUNT(*) FILTER (WHERE Json_ext->>'instruction' = 'INSTRUCTION_NIVEAU_PRIMAIRE_NON_ACHEVE') as primary_incomplete,
                    COUNT(*) FILTER (WHERE Json_ext->>'instruction' LIKE '%PRIMAIRE_ACHEVE%') as primary_complete,
                    COUNT(*) FILTER (WHERE Json_ext->>'instruction' LIKE '%SECONDAIRE%') as secondary_level,
                    
                    -- Health
                    COUNT(*) FILTER (WHERE Json_ext->>'handicap' = 'OUI') as with_disability,
                    COUNT(*) FILTER (WHERE Json_ext->>'maladie_chro' = 'OUI') as with_chronic_disease,
                    COUNT(*) FILTER (WHERE Json_ext->>'prob_sante' = 'OUI') as with_health_issues,
                    
                    -- Household roles
                    COUNT(*) FILTER (WHERE Json_ext->>'est_chef' = 'OUI') as household_heads,
                    COUNT(*) FILTER (WHERE Json_ext->>'lien' = 'EPOUX' OR Json_ext->>'lien' = 'EPOUSE') as spouses,
                    COUNT(*) FILTER (WHERE Json_ext->>'lien' LIKE '%ENFANT%') as children,
                    
                    -- Nationality
                    COUNT(*) FILTER (WHERE Json_ext->>'nationalite' = 'NATIONALITE_BURUNDAISE') as burundian,
                    COUNT(*) FILTER (WHERE Json_ext->>'nationalite' != 'NATIONALITE_BURUNDAISE') as foreign_nationals
                    
                FROM individual_individual
                WHERE "isDeleted" = false
            """)
            
            columns = [col[0] for col in cursor.description]
            result = dict(zip(columns, cursor.fetchone()))
            
            # Cache for 1 hour
            cache.set(cache_key, result, 3600)
            return result
    
    @staticmethod
    def get_beneficiary_payment_status():
        """
        Get payment status from group beneficiary JSON data
        """
        cache_key = 'dashboard_payment_status'
        cached = cache.get(cache_key)
        if cached:
            return cached
        
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    -- Total beneficiaries
                    COUNT(*) as total_beneficiaries,
                    
                    -- Payment status
                    COUNT(*) FILTER (WHERE Json_ext->'moyen_paiement'->>'etat' = 'ATTRIBUE') as payment_assigned,
                    COUNT(*) FILTER (WHERE Json_ext->'moyen_paiement'->>'status' = 'SUCCESS') as payment_successful,
                    COUNT(*) FILTER (WHERE Json_ext->'moyen_paiement' IS NOT NULL) as has_payment_method,
                    
                    -- Payment providers
                    COUNT(*) FILTER (WHERE Json_ext->'moyen_paiement'->>'agence' = 'ECONET') as econet_users,
                    COUNT(*) FILTER (WHERE Json_ext->'moyen_paiement'->>'agence' = 'LUMICASH') as lumicash_users,
                    
                    -- Active status
                    COUNT(*) FILTER (WHERE status = 'ACTIVE') as active_beneficiaries,
                    COUNT(*) FILTER (WHERE Json_ext->>'etat' = 'INSCRIT') as enrolled,
                    
                    -- PMT scores distribution
                    PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY CAST(NULLIF(Json_ext->>'score_pmt_initial', '') AS FLOAT)) as pmt_q1,
                    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY CAST(NULLIF(Json_ext->>'score_pmt_initial', '') AS FLOAT)) as pmt_median,
                    PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY CAST(NULLIF(Json_ext->>'score_pmt_initial', '') AS FLOAT)) as pmt_q3,
                    
                    -- Location coverage
                    COUNT(DISTINCT Json_ext->>'province_code') as provinces_covered,
                    COUNT(DISTINCT Json_ext->>'commune_code') as communes_covered,
                    COUNT(DISTINCT Json_ext->>'colline_code') as collines_covered
                    
                FROM social_protection_groupbeneficiary
                WHERE "isDeleted" = false
            """)
            
            columns = [col[0] for col in cursor.description]
            result = dict(zip(columns, cursor.fetchone()))
            
            # Cache for 30 minutes
            cache.set(cache_key, result, 1800)
            return result
    
    @staticmethod
    def get_location_breakdown(province_code=None, commune_code=None):
        """
        Get detailed location breakdown with optional filtering
        """
        cache_key = f'dashboard_location_{province_code}_{commune_code}'
        cached = cache.get(cache_key)
        if cached:
            return cached
        
        where_clause = ["g.\"isDeleted\" = false", "g.Json_ext->>'etat' = 'INSCRIT'"]
        params = []
        
        if province_code:
            where_clause.append("g.Json_ext->>'province_code' = %s")
            params.append(province_code)
        
        if commune_code:
            where_clause.append("g.Json_ext->>'commune_code' = %s")
            params.append(commune_code)
        
        with connection.cursor() as cursor:
            query = f"""
                WITH household_stats AS (
                    SELECT 
                        g.Json_ext->>'province_code' as province,
                        g.Json_ext->>'commune_code' as commune,
                        g.Json_ext->>'colline_code' as colline,
                        COUNT(DISTINCT g."UUID") as households,
                        COUNT(DISTINCT i."UUID") as individuals,
                        AVG(CAST(NULLIF(g.Json_ext->>'score_pmt_initial', '') AS FLOAT)) as avg_pmt,
                        COUNT(*) FILTER (WHERE g.Json_ext->>'vulnerable_ressenti' = 'VULNERABILITE_RESSENTI_OUI') as vulnerable,
                        COUNT(*) FILTER (WHERE g.Json_ext->>'menage_mutwa' = 'OUI') as twa,
                        COUNT(*) FILTER (WHERE gb."UUID" IS NOT NULL) as beneficiaries
                    FROM individual_group g
                    LEFT JOIN individual_individual i ON i.Json_ext->>'social_id' LIKE g.Json_ext->>'social_id' || '%'
                    LEFT JOIN social_protection_groupbeneficiary gb ON gb.group_id = g."UUID"
                    WHERE {' AND '.join(where_clause)}
                    GROUP BY province, commune, colline
                )
                SELECT 
                    province,
                    commune,
                    colline,
                    households,
                    individuals,
                    ROUND(avg_pmt::numeric, 2) as avg_pmt_score,
                    vulnerable,
                    twa,
                    beneficiaries,
                    ROUND(100.0 * beneficiaries / NULLIF(households, 0), 2) as coverage_rate
                FROM household_stats
                ORDER BY province, commune, colline
            """
            
            cursor.execute(query, params)
            columns = [col[0] for col in cursor.description]
            results = [dict(zip(columns, row)) for row in cursor.fetchall()]
            
            # Cache for 2 hours
            cache.set(cache_key, results, 7200)
            return results

# Create indexes for JSON fields
CREATE_JSON_INDEXES = """
-- Indexes for individual_group JSON queries
CREATE INDEX IF NOT EXISTS idx_group_json_type_menage ON individual_group USING GIN ((Json_ext->'type_menage'));
CREATE INDEX IF NOT EXISTS idx_group_json_vulnerable ON individual_group USING GIN ((Json_ext->'vulnerable_ressenti'));
CREATE INDEX IF NOT EXISTS idx_group_json_location ON individual_group USING GIN ((Json_ext->'province_code'), (Json_ext->'commune_code'));
CREATE INDEX IF NOT EXISTS idx_group_json_pmt_score ON individual_group USING BTREE (CAST(NULLIF(Json_ext->>'score_pmt_initial', '') AS FLOAT));
CREATE INDEX IF NOT EXISTS idx_group_json_etat ON individual_group USING GIN ((Json_ext->'etat'));
CREATE INDEX IF NOT EXISTS idx_group_json_social_id ON individual_group USING GIN ((Json_ext->'social_id'));

-- Indexes for individual_individual JSON queries
CREATE INDEX IF NOT EXISTS idx_individual_json_sexe ON individual_individual USING GIN ((Json_ext->'sexe'));
CREATE INDEX IF NOT EXISTS idx_individual_json_education ON individual_individual USING GIN ((Json_ext->'va_ecole'), (Json_ext->'instruction'));
CREATE INDEX IF NOT EXISTS idx_individual_json_health ON individual_individual USING GIN ((Json_ext->'handicap'), (Json_ext->'maladie_chro'));
CREATE INDEX IF NOT EXISTS idx_individual_json_chef ON individual_individual USING GIN ((Json_ext->'est_chef'));
CREATE INDEX IF NOT EXISTS idx_individual_json_social_id ON individual_individual USING GIN ((Json_ext->'social_id'));

-- Indexes for social_protection_groupbeneficiary JSON queries
CREATE INDEX IF NOT EXISTS idx_beneficiary_json_payment ON social_protection_groupbeneficiary USING GIN ((Json_ext->'moyen_paiement'));
CREATE INDEX IF NOT EXISTS idx_beneficiary_json_location ON social_protection_groupbeneficiary USING GIN ((Json_ext->'province_code'), (Json_ext->'commune_code'));
CREATE INDEX IF NOT EXISTS idx_beneficiary_status_active ON social_protection_groupbeneficiary (status) WHERE status = 'ACTIVE';
"""