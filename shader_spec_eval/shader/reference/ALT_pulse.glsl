void mainImage(out vec4 fragColor, in vec2 fragCoord) {
    vec2 p = (fragCoord - 0.5 * iResolution.xy) / iResolution.y;
    float radius = 0.32 + 0.09 * cos(iTime * 1.7);
    float light = smoothstep(radius, 0.0, length(p));
    fragColor = vec4(vec3(0.08, 0.28, 1.0) * light, 1.0);
}
