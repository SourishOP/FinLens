import 'package:flutter/material.dart';

// Shared design tokens — HSBC visual identity.
const hsbcRed = Color(0xFFDB0011);
const hsbcDark = Color(0xFF111111);
const bgGrey = Color(0xFFF2F2F2);
const hsbcGrey = Color(0xFF767676);

class Fmt {
  // HSBC UK app uses GBP (£).
  static String money(num v, {bool sign = false}) {
    final neg = v < 0;
    final s = v.abs().toStringAsFixed(2);
    final parts = s.split('.');
    final intPart = parts[0]
        .replaceAllMapped(RegExp(r'(\d)(?=(\d{3})+$)'), (m) => '${m[1]},');
    final prefix = neg ? '-£' : (sign ? '+£' : '£');
    return '$prefix$intPart.${parts[1]}';
  }
}

BoxDecoration cardDecoration() => const BoxDecoration(
      color: Colors.white,
      borderRadius: BorderRadius.all(Radius.circular(8)),
    );

/// The HSBC hexagon mark — two red "wings" on white, as on the real brand.
class HsbcLogo extends StatelessWidget {
  final double size;
  const HsbcLogo({super.key, this.size = 32});

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: size,
      height: size,
      child: CustomPaint(painter: _HexPainter()),
    );
  }
}

class _HexPainter extends CustomPainter {
  @override
  void paint(Canvas canvas, Size s) {
    final w = s.width, h = s.height;
    final white = Paint()..color = Colors.white;
    final red = Paint()..color = hsbcRed;
    // white background square
    canvas.drawRect(Offset.zero & s, white);
    // the HSBC hexagon: a rectangle with triangular notches top/bottom,
    // formed by two red triangles left and right of a white vertical band.
    final cx = w / 2;
    // left red wing
    final left = Path()
      ..moveTo(0, 0)
      ..lineTo(cx, h / 2)
      ..lineTo(0, h)
      ..close();
    // right red wing
    final right = Path()
      ..moveTo(w, 0)
      ..lineTo(cx, h / 2)
      ..lineTo(w, h)
      ..close();
    // top & bottom red triangles
    final top = Path()
      ..moveTo(0, 0)
      ..lineTo(w, 0)
      ..lineTo(cx, h / 2)
      ..close();
    final bottom = Path()
      ..moveTo(0, h)
      ..lineTo(w, h)
      ..lineTo(cx, h / 2)
      ..close();
    canvas.drawPath(left, red);
    canvas.drawPath(right, red);
    canvas.drawPath(top, red);
    canvas.drawPath(bottom, red);
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}
