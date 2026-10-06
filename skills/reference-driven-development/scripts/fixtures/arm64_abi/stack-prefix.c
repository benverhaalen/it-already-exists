/* Owned control matching the scalar prefix of tonic's semantics dispatcher.
 * Eight integer-register arguments precede three stack integers. Floating
 * arguments use their own register bank and do not consume those slots.
 * This isolates layout; it does not execute any original app function. */
extern void observe(int platform_view_id, int scroll_children, int scroll_index);
__attribute__((noinline)) void semantics_prefix(
    void *receiver, int id, void *flags, int actions, int max_value_length,
    int current_value_length, int selection_base, int selection_extent,
    int platform_view_id, int scroll_children, int scroll_index) {
  observe(platform_view_id, scroll_children, scroll_index);
}
