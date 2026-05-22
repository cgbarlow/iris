-- Migration 084: rename seeded 'Quantified item' element template → 'Ingredient'.
--
-- Mirrors SQLite m079. User-facing rename only; same row, same stamp body,
-- same scope. Idempotent — WHERE clause guards on the pre-rename name.

UPDATE public.element_templates
SET
    name = 'Ingredient',
    description = 'Element with a numeric quantity + unit (groceries, ingredients, parts, stock items, line items in a list with totals). Pairs with the ''Shopping list'' / sum-by-unit aggregation profile.'
WHERE id = 'ea8829e5-6e3f-5cf6-b1cc-a5ad92312dbf'
  AND name = 'Quantified item';
