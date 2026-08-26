void mainImage(out vec4 fragColor, in vec2 fragCoord) {
    vec2 uv = fragCoord / iResolution.y;
    float aspect = iResolution.x / iResolution.y;
    float inside = step(length(uv - vec2(0.30 * aspect, 0.65)), 0.24);
    fragColor = vec4(mix(vec3(0.015), vec3(0.96, 0.14, 0.12), inside), 1.0);
}
