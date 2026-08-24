void mainImage(out vec4 fragColor, in vec2 fragCoord) {
    vec2 uv = fragCoord / iResolution.xy;
    float cycle = 0.75 + 0.25 * sin(iTime * 6.28318530718 / 3.5);
    vec3 col = vec3((0.15 + 0.85 * uv.x) * cycle, 0.06 * uv.x, 0.05 * uv.x);
    fragColor = vec4(col, 1.0);
}
