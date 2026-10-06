import io.flutter.plugin.common.StandardMessageCodec;
import java.util.*; import java.nio.*; import java.io.*;
public class WireVectors {
 static class Wrapped {Object value; int tag; Wrapped(int t,Object v) {tag=t;value=v;}}
 static class Codec extends StandardMessageCodec {
  protected void writeValue(ByteArrayOutputStream stream,Object value) {
   if(value instanceof Wrapped) {Wrapped w=(Wrapped)value;stream.write(w.tag);writeValue(stream,w.value);}
   else super.writeValue(stream,value);
  }
 }
 static void emit(String name,Object value) {
  ByteBuffer b=new Codec().encodeMessage(value);b.flip();StringBuilder s=new StringBuilder();while(b.hasRemaining())s.append(String.format("%02x",b.get()&255));
  System.out.println(name+" "+s);
 }
 public static void main(String[] args) {
  emit("primitives",Arrays.asList(true,false,1,1.0,9007199254740993L,null,"é"));
  emit("nested-alignment",Arrays.asList(new Wrapped(200,Arrays.asList(new Wrapped(201,0.5),false)),new int[]{-1,2147483647},new long[]{Long.MIN_VALUE,Long.MAX_VALUE},new float[]{1.5f,-2.5f},new double[]{-0.0,Double.POSITIVE_INFINITY},new byte[]{0,1,(byte)255}));
  Map<Object,Object> map=new LinkedHashMap<>();map.put(1,"integer key");map.put(true,Arrays.asList(2.0));emit("map",map);
  emit("size254","x".repeat(254));emit("size65536","y".repeat(65536));
  emit("bigint",new java.math.BigInteger("-123456789abcdef",16));
 }
}