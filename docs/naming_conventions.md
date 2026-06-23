# Horse Management naming conventions

The app follows these conventions so later modules remain predictable.

## DocTypes

- Use singular, descriptive DocType names: `Horse`, `Feeding Session`.
- Use child-table DocTypes for rows that only exist inside a parent document.
- Use master records for reusable reference data such as horses and foods.
- Use submittable transaction DocTypes for completed operational or historical records.

## Fields

- Use lowercase `snake_case` field names.
- Include the entity in its display-name field: `horse_name`, `food_name`.
- Store measurements as numeric fields and keep the unit in a separate field.
- Link fields use the linked entity name: `horse`, `food`.
- Date and time fields state their meaning: `session_date`, `session_time`.

## Document names

- Human-recognizable master records use their required name field.
- Transactions use uppercase series with a year and sequence number.
- Feeding sessions use `FEED-SESSION-.YYYY.-.####`.

## History

- Draft operational records may be edited.
- Submitted records are historical records and must be cancelled and amended rather than silently rewritten.
