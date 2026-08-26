void mainImage(out vec4 fragColor, in vec2 fragCoord) {
    vec2 uv = fragCoord / iResolution.y;
    vec2 centre = vec2(0.30 * iResolution.x / iResolution.y, 0.65);
    float inside = step(length(uv - centre), 0.18);
    fragColor = vec4(mix(vec3(0.015), vec3(0.96, 0.14, 0.12), inside), 1.0);
}
