void mainImage(out vec4 fragColor, in vec2 fragCoord) {
    vec2 st = fragCoord / iResolution.xy;
    float v = dot(st, vec2(0.5));
    fragColor = vec4(vec3(0.02, 0.12 + 0.88 * v, 0.04), 1.0);
}
