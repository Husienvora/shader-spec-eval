void mainImage(out vec4 fragColor, in vec2 fragCoord) {
    vec2 uv = fragCoord / iResolution.xy;
    float t = uv.x;                       // deliberately ignores iTime
    vec3 col = vec3(0.15 + 0.85 * t, 0.06 * t, 0.05 * t);
    fragColor = vec4(col, 1.0);
}
