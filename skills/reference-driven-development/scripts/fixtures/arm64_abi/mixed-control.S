.text
.p2align 2
.globl _android_mixed_call
_android_mixed_call:
  sub sp, sp, #64
  stp x29, x30, [sp, #48]
  mov x16, x0
  str xzr, [sp]
  str xzr, [sp, #8]
  mov w9, #-11
  str w9, [sp]
  mov w9, #22
  str w9, [sp, #8]
  fmov d16, #9.0
  str d16, [sp, #16]
  mov x9, #12345
  str x9, [sp, #24]
  mov x9, #1
  str x9, [sp, #32]
  mov w0, #1
  mov w1, #2
  mov w2, #3
  mov w3, #4
  mov w4, #5
  mov w5, #6
  mov w6, #7
  mov w7, #8
  fmov d0, #1.0
  fmov d1, #2.0
  fmov d2, #3.0
  fmov d3, #4.0
  fmov d4, #5.0
  fmov d5, #6.0
  fmov d6, #7.0
  fmov d7, #8.0
  blr x16
  ldp x29, x30, [sp, #48]
  add sp, sp, #64
  ret
