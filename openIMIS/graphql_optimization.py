from promise import Promise
from promise.dataloader import DataLoader
from django.core.cache import cache
import json

class BeneficiaryDataLoader(DataLoader):
    """
    DataLoader for batching and caching beneficiary queries
    """
    def batch_load_fn(self, keys):
        from social_protection.models import Beneficiary
        
        # Check cache first
        cached_results = {}
        uncached_keys = []
        
        for key in keys:
            cached = cache.get(f'beneficiary_{key}')
            if cached:
                cached_results[key] = cached
            else:
                uncached_keys.append(key)
        
        # Fetch uncached data
        if uncached_keys:
            beneficiaries = Beneficiary.objects.select_related(
                'individual',
                'benefit_plan'
            ).filter(id__in=uncached_keys)
            
            beneficiary_dict = {str(b.id): b for b in beneficiaries}
            
            # Cache the results
            for key, beneficiary in beneficiary_dict.items():
                cache.set(f'beneficiary_{key}', beneficiary, 300)  # 5 minutes
            
            # Merge with cached results
            cached_results.update(beneficiary_dict)
        
        # Return in the same order as keys
        return Promise.resolve([
            cached_results.get(str(key)) for key in keys
        ])

class LocationDataLoader(DataLoader):
    """
    DataLoader for location hierarchy queries
    """
    def batch_load_fn(self, keys):
        from location.models import Location
        
        locations = Location.objects.select_related(
            'parent',
            'parent__parent'
        ).filter(id__in=keys)
        
        location_dict = {str(l.id): l for l in locations}
        
        return Promise.resolve([
            location_dict.get(str(key)) for key in keys
        ])

# GraphQL context with DataLoaders
def get_data_loaders():
    return {
        'beneficiary_loader': BeneficiaryDataLoader(),
        'location_loader': LocationDataLoader(),
    }

# Optimized GraphQL resolver
def resolve_dashboard_summary(self, info, **kwargs):
    """
    Optimized resolver using cache and DataLoader
    """
    cache_key = f"dashboard_summary_{json.dumps(kwargs, sort_keys=True)}"
    cached_result = cache.get(cache_key)
    
    if cached_result:
        return cached_result
    
    # Use DataLoader for efficient querying
    context = info.context
    loaders = context.get('loaders', {})
    
    # Your optimized query logic here
    result = {
        # ... dashboard data
    }
    
    # Cache the result
    cache.set(cache_key, result, 3600)  # 1 hour
    
    return result