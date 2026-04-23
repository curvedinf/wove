# Debugging & Introspection

Need to see what's going on under the hood?

- `with weave(debug=True) as w:`: Prints a detailed, color-coded execution plan to the console before running.
- `w.execution_plan`: After the block, this dictionary contains the full dependency graph and execution tiers.
- `w.result.timings`: A dictionary mapping each task name to its execution duration in seconds.

## Data-Shaping Helper Functions

Wove provides a set of simple, composable helper functions for common data manipulation patterns.

- **`flatten(list_of_lists)`**: Converts a 2D iterable into a 1D list.
- **`fold(a_list, size)`**: Converts a 1D list into N smaller lists of `size` length.
- **`batch(a_list, count)`**: Converts a 1D list into `count` smaller lists of N length.
- **`undict(a_dict)`**: Converts a dictionary into a list of `[key, value]` pairs.
- **`redict(list_of_pairs)`**: Converts a list of key-value pairs back into a dictionary.
- **`denone(an_iterable)`**: Removes all `None` values from an iterable.
