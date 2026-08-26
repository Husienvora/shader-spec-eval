void mainImage(out vec4 fragColor, in vec2 fragCoord) {
    vec2 uv = fragCoord / iResolution.y;
    float aspect = iResolution.x / iResolution.y;
    vec2 centre = vec2((0.25 + 0.25 * iTime) * aspect, 0.50);
    float inside = step(length(uv - centre), 0.10);
    fragColor = vec4(mix(vec3(0.012), vec3(0.95), inside), 1.0);
}
