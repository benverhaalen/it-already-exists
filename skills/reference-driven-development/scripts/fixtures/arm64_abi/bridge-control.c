#include <stdio.h>
typedef long (*reader)(void *, int, void *, int, int, int, int, int, int, int, int);
extern long android_layout_call(reader function);
extern long bridged_read(void *, int, void *, int, int, int, int, int, int, int, int);
__attribute__((noinline)) long darwin_read(
    void *receiver, int id, void *flags, int actions, int max_value_length,
    int current_value_length, int selection_base, int selection_extent,
    int platform_view_id, int scroll_children, int scroll_index) {
  return platform_view_id * 10000L + scroll_children * 100L + scroll_index;
}
__attribute__((ms_abi,noinline)) long compiler_bridged_read(
    void *receiver, int id, void *flags, int actions, int max_value_length,
    int current_value_length, int selection_base, int selection_extent,
    int platform_view_id, int scroll_children, int scroll_index) {
  return darwin_read(receiver,id,flags,actions,max_value_length,current_value_length,
      selection_base,selection_extent,platform_view_id,scroll_children,scroll_index);
}
int main(void) {
  long direct = android_layout_call(darwin_read);
  long bridged = android_layout_call(bridged_read);
  printf("ANDROID_LAYOUT_CONTROL direct=%ld bridged=%ld expected=112233\n", direct, bridged);
  long compiled = android_layout_call((reader)compiler_bridged_read);
  printf("COMPILER_BRIDGE_CONTROL result=%ld expected=112233\n", compiled);
  return direct == 110022 && bridged == 112233 && compiled == 112233 ? 0 : 1;
}
