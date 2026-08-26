void mainImage(out vec4 fragColor, in vec2 fragCoord) {
    vec2 p = fragCoord / iResolution.y;
    float aspect = iResolution.x / iResolution.y;
    vec2 d = p - vec2((0.25 + iTime * 0.25) * aspect, 0.50);
    float mask = 1.0 - step(0.01, dot(d, d));
    fragColor = vec4(mix(vec3(0.012), vec3(0.95), mask), 1.0);
}
