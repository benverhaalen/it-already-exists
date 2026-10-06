.text
.p2align 2
.globl _android_layout_call
_android_layout_call:
  sub sp, sp, #48
  stp x29, x30, [sp, #32]
  mov x16, x0
  str xzr, [sp]
  str xzr, [sp, #8]
  str xzr, [sp, #16]
  mov w9, #11
  str w9, [sp]
  mov w9, #22
  str w9, [sp, #8]
  mov w9, #33
  str w9, [sp, #16]
  blr x16
  ldp x29, x30, [sp, #32]
  add sp, sp, #48
  ret
.p2align 2
.globl _bridged_read
_bridged_read:
  sub sp, sp, #32
  stp x29, x30, [sp, #16]
  ldr w9, [sp, #32]
  ldr w10, [sp, #40]
  ldr w11, [sp, #48]
  stp w9, w10, [sp]
  str w11, [sp, #8]
  bl _darwin_read
  ldp x29, x30, [sp, #16]
  add sp, sp, #32
  ret
