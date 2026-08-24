void mainImage(out vec4 fragColor, in vec2 fragCoord) {
    vec2 uv = (fragCoord - 0.5*iResolution.xy) / iResolution.y;
    float r = length(uv);
    float a = atan(uv.y, uv.x) + iTime * 0.6;
    float petals = 0.5 + 0.5*cos(a * 5.0);             // 5 not 6
    float shape = smoothstep(0.42*(0.45+0.55*petals), 0.0, r);
    float i = clamp(shape + exp(-r*r*9.0)*0.6, 0.0, 1.0);
    fragColor = vec4(vec3(0.08,0.75,1.0) * i, 1.0);
}
