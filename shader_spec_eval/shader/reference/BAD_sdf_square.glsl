void mainImage(out vec4 fragColor, in vec2 fragCoord) {
    vec2 uv = (fragCoord - 0.5 * iResolution.xy) / min(iResolution.x, iResolution.y);
    float d = max(abs(uv.x), abs(uv.y)) - 0.30;
    float inside = step(d, 0.0);
    vec3 col = mix(vec3(0.02), vec3(1.0, 0.55, 0.08), inside);
    fragColor = vec4(col, 1.0);
}
