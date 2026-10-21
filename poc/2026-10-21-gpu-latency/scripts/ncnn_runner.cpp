// AGPL-3.0-only. Persistent binary float32 CHW stdin / float32 output protocol.
#include <net.h>
#include <gpu.h>
#include <cstdio>
#include <cstdint>
#include <chrono>
int main(int argc,char**argv) {
 if(argc!=4) return 2;
 ncnn::create_gpu_instance();
 int gpu=ncnn::get_default_gpu_index();
 if(gpu<0) return 3;
 fprintf(stderr,"ncnn GPU %d: %s\n",gpu,ncnn::get_gpu_info(gpu).device_name());
 ncnn::Net net; net.opt.use_vulkan_compute=true; net.set_vulkan_device(gpu);
 if(net.load_param(argv[1]) || net.load_model(argv[2])) return 4;
 int size=atoi(argv[3]); ncnn::Mat in(size,size,3);
 while(fread(in.data,sizeof(float),size*size*3,stdin)==(size_t)size*size*3) {
  auto start=std::chrono::steady_clock::now();
  auto ex=net.create_extractor();
  if(ex.input("in0",in)) return 5;
  ncnn::Mat out; if(ex.extract("out0",out)) return 6;
  double ms=std::chrono::duration<double,std::milli>(std::chrono::steady_clock::now()-start).count();
  fwrite(&ms,sizeof(ms),1,stdout);
  int32_t dims[3]={out.w,out.h,out.c};
  fwrite(dims,4,3,stdout);
  for(int c=0;c<out.c;c++) fwrite(out.channel(c),4,out.w*out.h,stdout);
  fflush(stdout);
 }
 return 0;
}
