// Pin assignment check for the iCE40UP5K-SG48 (hardware/fpga-pins.csv).
// Not the probe gateware: it only exercises every assigned pin with the IO type it
// will have, so that nextpnr validates the placement and reports the QSPI timing.
module top (
    // MCU link
    input  wire       qspi_clk,      // pin 15, SPI_SCK (not a GBIN)
    input  wire       qspi_ncs,      // pin 16, SPI_SS
    inout  wire [3:0] qspi_io,       // pins 17, 14, 12, 13
    output wire       fpga_irq,
    input  wire       pps,
    input  wire       refclk,        // pin 20, GBIN
    // Shield
    output wire       sync_out,
    input  wire       sync_in,       // pin 23, GBIN
    inout  wire [15:0] shield_io,
    output wire       shield_oe_n,   // pin 39, RGB0, open drain
    // Target (3.3 V side of the translators)
    input  wire       tgt_uart_rx,
    output wire       tgt_uart_tx,
    output wire       tgt_io0,
    output wire       tgt_nrst,
    input  wire       tgt_swo,
    output wire       tgt_tdi,
    output wire       tgt_swdio_dir,
    output wire       tgt_swclk,
    inout  wire       tgt_swdio
);
    // QSPI DTR receive and transmit: DDR registers in the IO cells, clocked by qspi_clk.
    wire [3:0] rx_rise, rx_fall;
    reg  [3:0] tx_rise, tx_fall;
    reg        qspi_oe;
    genvar i;
    generate for (i = 0; i < 4; i = i + 1) begin : g_qspi
        SB_IO #(.PIN_TYPE(6'b1100_00)) io (
            .PACKAGE_PIN(qspi_io[i]),
            .INPUT_CLK(qspi_clk), .OUTPUT_CLK(qspi_clk), .CLOCK_ENABLE(1'b1),
            .OUTPUT_ENABLE(qspi_oe),
            .D_OUT_0(tx_rise[i]), .D_OUT_1(tx_fall[i]),
            .D_IN_0(rx_rise[i]), .D_IN_1(rx_fall[i]));
    end endgenerate

    reg [31:0] shreg;
    always @(posedge qspi_clk) begin
        if (qspi_ncs) begin
            shreg <= 32'd0; qspi_oe <= 1'b0;
        end else begin
            shreg <= {shreg[23:0], rx_rise, rx_fall};
            qspi_oe <= shreg[31];
            tx_rise <= shreg[3:0] ^ shreg[11:8];
            tx_fall <= shreg[7:4] ^ shreg[15:12];
        end
    end

    // Reference clock domain: target and shield logic.
    reg [31:0] cnt;
    reg        pps_q, sync_q, swdio_q, swo_q, rx_q;
    reg [15:0] shield_q;
    always @(posedge refclk) begin
        cnt      <= cnt + 1'b1;
        pps_q    <= pps;
        sync_q   <= sync_in;
        swdio_q  <= tgt_swdio;
        swo_q    <= tgt_swo;
        rx_q     <= tgt_uart_rx;
        shield_q <= shield_io;
    end

    assign fpga_irq      = shreg[0] ^ pps_q;
    assign sync_out      = sync_q ^ cnt[3];
    assign tgt_swclk     = cnt[1];
    assign tgt_swdio_dir = cnt[7];
    assign tgt_swdio     = tgt_swdio_dir ? cnt[2] : 1'bz;
    assign tgt_tdi       = swo_q;
    assign tgt_uart_tx   = rx_q;
    assign tgt_io0       = cnt[20];
    assign tgt_nrst      = cnt[21];
    assign shield_io     = cnt[8] ? (shield_q ^ cnt[31:16]) : 16'bz;

    // RGB0 as a plain IO emulating open drain (pulled up on the board): drive low or release.
    wire oe_drive = ~(swdio_q & cnt[9]);
    SB_IO #(.PIN_TYPE(6'b1010_01)) oe_n (
        .PACKAGE_PIN(shield_oe_n),
        .OUTPUT_ENABLE(oe_drive),
        .D_OUT_0(1'b0));
endmodule
