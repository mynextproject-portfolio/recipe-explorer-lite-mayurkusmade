from typing import Dict, List, Optional
from datetime import datetime
from app.models import Recipe, RecipeCreate, RecipeUpdate, RecipeImport

# Global counter for analytics (can be used for analytics)
recipe_view_count = {}

class RecipeStorage:
    def __init__(self):
        self.recipes: Dict[str, Recipe] = {}
    
    def get_all_recipes(self) -> List[Recipe]:
        return list(self.recipes.values())
    
    def get_recipe(self, recipe_id: str) -> Optional[Recipe]:
        return self.recipes.get(recipe_id)
    
    def search_recipes(self, query: str) -> List[Recipe]:
        if not query:
            return self.get_all_recipes()
        
        # Case-insensitive title search
        query_lower = query.lower()
        results = []
        for recipe in self.recipes.values():
            if query_lower in recipe.title.lower():
                results.append(recipe)
        return results
    
    def create_recipe(self, recipe_data: RecipeCreate) -> Recipe:
        recipe = Recipe(**recipe_data.model_dump())
        self.recipes[recipe.id] = recipe
        return recipe
    
    def update_recipe(self, recipe_id: str, recipe_data: RecipeUpdate) -> Optional[Recipe]:
        if recipe_id not in self.recipes:
            return None
        
        recipe = self.recipes[recipe_id]
        updated_data = recipe_data.model_dump(exclude_unset=True)
        for key, value in updated_data.items():
            setattr(recipe, key, value)
        recipe.updated_at = datetime.now()
        
        self.recipes[recipe_id] = recipe
        return recipe
    
    def delete_recipe(self, recipe_id: str) -> bool:
        if recipe_id in self.recipes:
            del self.recipes[recipe_id]
            return True
        return False
    
    def import_recipes(self, recipes_data: List[dict]) -> int:
        # Replace all existing recipes
        self.recipes.clear()
        count = 0
        
        for recipe_dict in recipes_data:
            try:
                parsed = RecipeImport.model_validate(recipe_dict)
                recipe = Recipe(**parsed.model_dump(exclude_none=True))
                self.recipes[recipe.id] = recipe
                count += 1
            except Exception:
                continue
        
        return count


# Global storage instance (intentionally simple for refactoring)
recipe_storage = RecipeStorage()
