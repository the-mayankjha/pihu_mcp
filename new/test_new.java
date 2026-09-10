public class test_new {
    public static void main(String[] args) {
        int rows = 5;
        System.out.println("Right Triangle Star Pattern:");
        for (int i = 1; i <= rows; i++) {
            for (int j = 1; j <= i; j++) {
                System.out.print("* ");
            }
            System.out.println();
        }
    }
}
