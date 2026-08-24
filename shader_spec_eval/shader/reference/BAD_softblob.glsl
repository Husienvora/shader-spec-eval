void mainImage(out vec4 fragColor, in vec2 fragCoord) {
    vec2 uv = (fragCoord - 0.5*iResolution.xy) / min(iResolution.x, iResolution.y);
    float i = exp(-length(uv)*length(uv)*6.0);         // gaussian, no hard edge
    fragColor = vec4(vec3(1.0,0.55,0.08) * i, 1.0);
}
