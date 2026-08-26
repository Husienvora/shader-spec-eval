void mainImage(out vec4 fragColor, in vec2 fragCoord) {
    int stripe = int(floor(6.0 * fragCoord.x / iResolution.x));
    vec3 dark = vec3(0.015);
    vec3 bright = vec3(0.92, 0.04, 1.0);
    fragColor = vec4((stripe % 2 == 0) ? dark : bright, 1.0);
}
