void mainImage(out vec4 fragColor, in vec2 fragCoord) {
    vec2 uv = fragCoord / iResolution.xy;
    float v = 0.5 * (uv.x + uv.y);
    fragColor = vec4(0.04 * v, 0.15 + 0.85 * v, 0.06 * v, 1.0);
}
