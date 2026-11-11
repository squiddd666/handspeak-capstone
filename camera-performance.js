// Software WebGL can initialize successfully yet be slower than CPU inference.
export function preferredVisionDelegate(createCanvas=()=>document.createElement('canvas')){
 let gl;
 try{
  gl=createCanvas().getContext('webgl2');
  if(!gl)return 'CPU';
  const extension=gl.getExtension('WEBGL_debug_renderer_info');
  const renderer=extension?gl.getParameter(extension.UNMASKED_RENDERER_WEBGL):gl.getParameter(gl.RENDERER);
  return /swiftshader|llvmpipe|softpipe|software/i.test(String(renderer))?'CPU':'GPU';
 }catch{return 'CPU';}
 finally{try{gl?.getExtension('WEBGL_lose_context')?.loseContext();}catch{}}
}
