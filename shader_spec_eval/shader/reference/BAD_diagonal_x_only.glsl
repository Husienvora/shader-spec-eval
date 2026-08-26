void mainImage(out vec4 fragColor, in vec2 fragCoord) {
    float v = fragCoord.x / iResolution.x;
    fragColor = vec4(0.02, 0.12 + 0.88 * v, 0.04, 1.0);
}
