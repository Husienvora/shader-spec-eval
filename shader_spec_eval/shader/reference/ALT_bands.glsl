void mainImage(out vec4 fragColor, in vec2 fragCoord) {
    float band = min(4.0, trunc(5.0 * fragCoord.x / iResolution.x));
    vec3 shade = vec3(band * 0.25);
    fragColor = vec4(shade, 1.0);
}
